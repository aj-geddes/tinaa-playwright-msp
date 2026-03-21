# Backup & Restore

This guide covers backing up the TINAA MSP database, managing Alembic schema migrations, and recovering from data loss or corruption.

---

## What to back up

| Component | Contains | Criticality |
|-----------|---------|-------------|
| PostgreSQL database | All products, playbooks, test results, metrics, quality scores, alerts | Critical |
| `.env` file | API keys, secrets, database credentials | Critical |
| `tinaa/frontend/static/docs/` | Documentation files | Medium |
| Playbook YAML files (if stored in repo) | Test definitions | Low (in git) |
| Playwright screenshots | Test run artefacts | Low |

---

## Database backup procedures

### PostgreSQL / TimescaleDB

**On-demand backup:**

```bash
# Using pg_dump (recommended — consistent, cross-version portable)
pg_dump --host=localhost --port=5432 --username=tinaa \
  --format=custom --compress=9 \
  --file=/backups/tinaa-$(date +%Y%m%d-%H%M%S).pgdump \
  tinaa
```

**Restore from backup:**

```bash
pg_restore --host=localhost --port=5432 --username=tinaa \
  --dbname=tinaa_restore \
  --no-owner --no-privileges \
  /backups/tinaa-20260321-103000.pgdump
```

**Automated daily backup via cron:**

```bash
# /etc/cron.d/tinaa-backup
0 2 * * * postgres pg_dump -Fc tinaa \
  > /backups/tinaa-$(date +\%Y\%m\%d).pgdump && \
  find /backups -name "tinaa-*.pgdump" -mtime +30 -delete
```

This creates a daily backup at 02:00 and removes backups older than 30 days.

**Docker Compose backup:**

```bash
docker compose exec postgres pg_dump -U tinaa -Fc tinaa \
  > /backups/tinaa-$(date +%Y%m%d-%H%M%S).pgdump
```

### TimescaleDB-specific considerations

TimescaleDB hypertables store metrics in compressed chunks. When using `pg_dump`, all data is exported correctly — TimescaleDB compression is transparent to `pg_dump`. However, restoring to a PostgreSQL instance without the TimescaleDB extension will fail on hypertable creation.

Always restore to a PostgreSQL instance with the same TimescaleDB version installed:

```bash
# Verify TimescaleDB version before restoring
psql -d tinaa -c "SELECT extversion FROM pg_extension WHERE extname='timescaledb';"
```

### SQLite (development only)

```bash
# Simple file copy (safe only when TINAA is stopped or in read-only mode)
cp tinaa.db tinaa-backup-$(date +%Y%m%d-%H%M%S).db

# Online backup using SQLite's built-in backup API
python -c "
import sqlite3
src = sqlite3.connect('tinaa.db')
dst = sqlite3.connect('tinaa-backup.db')
src.backup(dst)
dst.close()
src.close()
print('Backup complete')
"
```

---

## Migration management with Alembic

TINAA uses [Alembic](https://alembic.sqlalchemy.org/) for database schema migrations. All schema changes are version-controlled in `alembic/versions/`.

### View current migration state

```bash
alembic current
# Example output: fc5241a12fa5 (head)
```

### Apply all pending migrations

```bash
alembic upgrade head
```

### Apply to a specific revision

```bash
alembic upgrade fc5241a12fa5
```

### Downgrade one revision

```bash
alembic downgrade -1
```

### Downgrade to a specific revision

```bash
alembic downgrade abc123def456
```

### View migration history

```bash
alembic history --verbose
```

### Generate a new migration

After modifying SQLAlchemy models, auto-generate a migration:

```bash
alembic revision --autogenerate -m "add_quality_history_table"
```

Always review the generated migration file before applying it to production.

### Migration best practices

- Always run `alembic upgrade head` after deploying a new version of TINAA.
- Back up the database before running any migration that includes `DROP`, `ALTER COLUMN`, or bulk data transforms.
- Test migrations on a staging database first.
- Never manually modify the `alembic_version` table.

---

## Disaster recovery

### Recovery time objectives

| Scenario | Target RTO | Target RPO |
|----------|-----------|-----------|
| Database host failure | 30 minutes | 24 hours (daily backup) |
| Accidental table drop | 15 minutes | 24 hours (daily backup) |
| Data corruption | 1 hour | 24 hours (daily backup) |
| Full instance loss | 2 hours | 24 hours (daily backup) |

Reduce RPO to near-zero by enabling PostgreSQL streaming replication with a hot standby.

### Full instance recovery procedure

1. **Provision a new host** meeting the system requirements.
2. **Install TINAA MSP** following the [Installation guide](installation.md).
3. **Restore environment variables** from your secrets manager or `.env` backup.
4. **Restore the database:**
   ```bash
   psql -U postgres -c "CREATE DATABASE tinaa OWNER tinaa;"
   psql -U postgres -d tinaa -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"
   pg_restore -U tinaa -d tinaa /backups/tinaa-latest.pgdump
   ```
5. **Verify migration state:**
   ```bash
   alembic current  # should show the latest migration revision
   ```
6. **Start TINAA services:**
   ```bash
   docker compose up -d
   ```
7. **Verify health:**
   ```bash
   curl http://localhost:8765/health
   ```
8. **Run a test run** to confirm the system is fully operational.

### Point-in-time recovery with PostgreSQL WAL

For production deployments requiring RPO < 24 hours, enable WAL archiving and use `pg_basebackup` + WAL replay for point-in-time recovery:

```bash
# postgresql.conf
archive_mode = on
archive_command = 'cp %p /wal-archive/%f'
wal_level = replica
```

Consult the [PostgreSQL PITR documentation](https://www.postgresql.org/docs/current/continuous-archiving.html) for full setup instructions.
