# Database Management

TINAA MSP uses PostgreSQL 15 with the TimescaleDB extension for production. This document covers the schema, hypertable configuration, data retention, Alembic migrations, and performance tuning.

---

## Schema overview (13 tables)

| Table | Type | Description |
|-------|------|-------------|
| `organisations` | Regular | Teams / tenants using the platform |
| `products` | Regular | Monitored applications (one per app) |
| `environments` | Regular | Deployment environments per product |
| `endpoints` | Regular | Monitored URL paths per environment |
| `playbooks` | Regular | Test playbook definitions (YAML stored as JSON) |
| `test_runs` | Regular | Individual test execution records |
| `test_run_results` | Regular | Per-step results for each test run |
| `quality_scores` | Regular | Historical quality score snapshots |
| `alert_rules` | Regular | Configured alert rule definitions |
| `alerts` | Regular | Fired alert instances and their lifecycle |
| `endpoint_metrics` | **Hypertable** | Time-series: response time, status, availability |
| `web_vitals` | **Hypertable** | Time-series: LCP, FCP, CLS, INP per endpoint |
| `baselines` | Regular | Computed baseline statistics per endpoint |

### Key relationships

```
organisations (1) ──< (N) products
products      (1) ──< (N) environments
environments  (1) ──< (N) endpoints
environments  (1) ──< (N) endpoint_metrics [hypertable]
endpoints     (1) ──< (N) web_vitals [hypertable]
products      (1) ──< (N) playbooks
products      (1) ──< (N) test_runs
test_runs     (1) ──< (N) test_run_results
products      (1) ──< (N) quality_scores
products      (1) ──< (N) alert_rules
alert_rules   (1) ──< (N) alerts
endpoints     (1) ──< (N) baselines
```

---

## TimescaleDB hypertables for metrics

TimescaleDB partitions `endpoint_metrics` and `web_vitals` into time-based chunks. This enables:
- Fast time-range queries (only the relevant chunks are scanned)
- Efficient compression of older chunks
- Automatic chunk management and data retention policies

### Hypertable configuration

```sql
-- endpoint_metrics hypertable (partition by 1 day)
SELECT create_hypertable('endpoint_metrics', 'measured_at',
  chunk_time_interval => INTERVAL '1 day');

-- Enable compression on chunks older than 7 days
ALTER TABLE endpoint_metrics SET (
  timescaledb.compress,
  timescaledb.compress_orderby = 'measured_at DESC',
  timescaledb.compress_segmentby = 'endpoint_id'
);
SELECT add_compression_policy('endpoint_metrics',
  compress_after => INTERVAL '7 days');

-- web_vitals hypertable
SELECT create_hypertable('web_vitals', 'collected_at',
  chunk_time_interval => INTERVAL '1 day');
ALTER TABLE web_vitals SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'endpoint_id'
);
SELECT add_compression_policy('web_vitals',
  compress_after => INTERVAL '7 days');
```

### Verifying hypertable status

```sql
SELECT hypertable_name,
  num_chunks,
  compression_enabled
FROM timescaledb_information.hypertables;

-- View chunk sizes
SELECT chunk_name, range_start, range_end,
  pg_size_pretty(total_bytes) AS size
FROM timescaledb_information.chunks
WHERE hypertable_name = 'endpoint_metrics'
ORDER BY range_start DESC
LIMIT 10;
```

---

## Data retention policies

### Default retention

| Data | Default retention | Rationale |
|------|-------------------|-----------|
| `endpoint_metrics` | 90 days | Long enough for baseline computation and trend analysis |
| `web_vitals` | 90 days | Aligns with metrics retention |
| `test_run_results` (detailed steps) | 30 days | Screenshots and step details consume disk |
| `quality_scores` | 365 days | Historical quality trends for annual reviews |
| `alerts` (resolved) | 180 days | Audit trail for incident retrospectives |

### Configuring retention with TimescaleDB policies

```sql
-- Drop endpoint_metrics chunks older than 90 days
SELECT add_retention_policy('endpoint_metrics',
  drop_after => INTERVAL '90 days');

-- Drop web_vitals chunks older than 90 days
SELECT add_retention_policy('web_vitals',
  drop_after => INTERVAL '90 days');
```

### Manual data purge

```sql
-- Purge test_run_results older than 30 days
DELETE FROM test_run_results
WHERE created_at < NOW() - INTERVAL '30 days';

-- Vacuum after large deletes
VACUUM ANALYZE test_run_results;
```

---

## Alembic migration procedures

### Standard upgrade

```bash
# Apply all pending migrations
alembic upgrade head

# Verify
alembic current   # should show the latest revision hash
```

### Pre-migration checklist

Before running a migration in production:
1. Back up the database (see [Backup & Restore](../admin/backup-restore.md)).
2. Run the migration on a staging database first.
3. Review the generated SQL: `alembic upgrade head --sql > migration-preview.sql`
4. Schedule a maintenance window for migrations involving table locks (e.g. `ALTER TABLE`).
5. Have the rollback command ready: `alembic downgrade -1`

### Creating a new migration

After modifying SQLAlchemy models in `tinaa/models/`:

```bash
# Auto-generate from model diff
alembic revision --autogenerate -m "add_column_products_team"

# Review the generated file in alembic/versions/
# Then apply
alembic upgrade head
```

### Dangerous migration patterns to avoid

| Pattern | Risk | Safe alternative |
|---------|------|-----------------|
| `ALTER TABLE ADD COLUMN NOT NULL` without default | Locks entire table | Add nullable first, backfill, then add NOT NULL |
| `DROP COLUMN` | Irreversible | Rename column, keep for one release cycle, then drop |
| `ALTER COLUMN TYPE` on large table | Long lock | Use `pg_repack` or add a new column + copy |
| Truncating hypertables | Permanent data loss | Use retention policies instead |

---

## Performance tuning

### PostgreSQL configuration for TINAA workloads

Add to `postgresql.conf`:

```ini
# Memory
shared_buffers = 2GB                  # 25% of available RAM
effective_cache_size = 6GB            # 75% of available RAM
work_mem = 64MB                       # per-sort operation
maintenance_work_mem = 512MB          # for VACUUM, index builds

# Write performance (time-series writes are high throughput)
synchronous_commit = off              # asynchronous commits (safe for metrics)
wal_compression = on
checkpoint_completion_target = 0.9

# Connection
max_connections = 100                 # use PgBouncer for > 100 connections

# Logging
log_min_duration_statement = 1000    # log queries taking > 1 s
log_autovacuum_min_duration = 500    # log slow autovacuum runs
```

### Useful indexes

These indexes are created by the Alembic migrations. Verify they exist:

```sql
-- Most important indexes for TINAA query patterns
SELECT indexname, tablename, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

-- Critical indexes to verify
-- endpoint_metrics: (endpoint_id, measured_at DESC) for time-range queries
-- test_runs: (product_id, created_at DESC) for history view
-- quality_scores: (product_id, computed_at DESC) for trend charts
-- alerts: (product_id, status) for active alert queries
```

### VACUUM and maintenance

TimescaleDB chunks are automatically managed, but regular tables need VACUUM:

```bash
# Manual vacuum on high-write tables
psql -d tinaa -c "VACUUM ANALYZE test_run_results;"
psql -d tinaa -c "VACUUM ANALYZE alerts;"

# Check autovacuum status
psql -d tinaa -c "
  SELECT relname, n_dead_tup, last_autovacuum, last_autoanalyze
  FROM pg_stat_user_tables
  ORDER BY n_dead_tup DESC
  LIMIT 10;
"
```
