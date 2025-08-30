# Security Policy and Scanning Guide

## 🔒 Security Overview

TINAA implements multiple layers of security to protect sensitive data and prevent unauthorized access. This document outlines our security practices and how to use the security scanning tools.

## 🛡️ Security Features

### Pre-Push Security Hook
A Git pre-push hook automatically runs security checks before allowing code to be pushed to the repository:
- Scans for hardcoded secrets and API keys
- Checks deployment files for exposed credentials
- Validates file permissions
- Runs static security analysis

### Security Scanning Tools

#### 1. Quick Security Scan
Run a comprehensive security scan:
```bash
./scripts/security-scan.sh
```

This checks for:
- Hardcoded secrets (API keys, passwords, tokens)
- Vulnerable dependencies
- Python security issues (via bandit)
- Insecure file permissions
- Docker security best practices
- Kubernetes security configurations
- Git history for accidentally committed secrets

#### 2. Manual Security Checks

**Secret Detection:**
```bash
# Install detect-secrets
pip install detect-secrets

# Scan entire repository
detect-secrets scan --all-files

# Scan specific directory
detect-secrets scan app/
```

**Python Security Analysis:**
```bash
# Install bandit
pip install bandit

# Run security analysis
bandit -r app/ -f json -o security-report.json

# View high severity issues only
bandit -r app/ -ll
```

**Dependency Vulnerabilities:**
```bash
# Install pip-audit
pip install pip-audit

# Check for vulnerable packages
pip-audit

# Get detailed descriptions
pip-audit --desc
```

## 🔐 Security Best Practices

### 1. Never Commit Secrets
- Use environment variables for API keys
- Store secrets in Kubernetes secrets or HashiCorp Vault
- Use placeholders like `YOUR_API_KEY_HERE` in examples

### 2. Secure Configuration
- All sensitive configuration should use environment variables
- Use `.env` files locally (never commit them)
- In production, use Kubernetes secrets or cloud secret managers

### 3. File Permissions
- Scripts should have permissions 755 or more restrictive
- Configuration files should be 644 or more restrictive
- Never use 777 permissions

### 4. Docker Security
- Always specify a non-root USER in Dockerfiles
- Use specific version tags, not `:latest`
- Minimize image layers and remove unnecessary packages
- Scan images with tools like Trivy or Snyk

### 5. Kubernetes Security
- Define SecurityContext for all pods
- Set resource limits and requests
- Use NetworkPolicies to restrict traffic
- Enable RBAC and use least privilege principles
- Regularly rotate secrets

## 🚨 Reporting Security Issues

If you discover a security vulnerability:

1. **Do NOT** create a public GitHub issue
2. Email security details to the maintainers
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if available)

## 📋 Security Checklist

Before pushing code:

- [ ] Run `./scripts/security-scan.sh`
- [ ] No hardcoded secrets or API keys
- [ ] All secrets use environment variables
- [ ] File permissions are appropriate
- [ ] No vulnerable dependencies
- [ ] Docker image follows security best practices
- [ ] Kubernetes manifests include security contexts
- [ ] Code passes static security analysis

## 🔄 Regular Security Maintenance

### Weekly
- Run dependency vulnerability scans
- Review security alerts from GitHub

### Monthly
- Update dependencies to latest secure versions
- Review and rotate API keys and secrets
- Audit file permissions

### Quarterly
- Full security audit
- Review security policies and update as needed
- Security training for team members

## 🛠️ Bypass Security Checks (Emergency Only)

In rare cases where you need to bypass security checks:

```bash
# Bypass pre-push hook (NOT RECOMMENDED)
git push --no-verify

# Skip specific detect-secrets check
# Add to .secrets.baseline after review
```

⚠️ **WARNING**: Only bypass security checks after thorough review and with team approval.

## 📚 Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE/SANS Top 25](https://cwe.mitre.org/top25/)
- [Kubernetes Security Best Practices](https://kubernetes.io/docs/concepts/security/)
- [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)

---

*Last Updated: 2025*
*Security Contact: [Add security contact email]*