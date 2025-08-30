#!/bin/bash
# TINAA Security Scanning Script
# Run comprehensive security checks on the codebase

set -e

echo "======================================"
echo "    TINAA Security Scanner v1.0      "
echo "======================================"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Results tracking
TOTAL_ISSUES=0
CRITICAL_ISSUES=0

# Function to print section headers
print_section() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# 1. Secret Detection
print_section "🔍 SECRET DETECTION"

echo "Checking for hardcoded secrets..."
SECRET_COUNT=0

# Common secret patterns to check
declare -A SECRET_PATTERNS=(
    ["Anthropic API Key"]="sk-ant-[a-zA-Z0-9-]{90,}"
    ["OpenAI API Key"]="sk-[a-zA-Z0-9]{48}"
    ["GitHub Token"]="gh[ps]_[a-zA-Z0-9]{36}"
    ["AWS Access Key"]="AKIA[0-9A-Z]{16}"
    ["Generic API Key"]="api[_-]?key.*=.*['\"][a-zA-Z0-9]{20,}"
)

for name in "${!SECRET_PATTERNS[@]}"; do
    pattern="${SECRET_PATTERNS[$name]}"
    if grep -r -E "$pattern" . --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=.venv --exclude="*.log" 2>/dev/null | grep -v "YOUR_.*_HERE" | grep -v "placeholder" | grep -v "example" | head -n 1 > /dev/null; then
        echo -e "${RED}❌ Found potential $name${NC}"
        ((SECRET_COUNT++))
        ((TOTAL_ISSUES++))
    fi
done

if [ $SECRET_COUNT -eq 0 ]; then
    echo -e "${GREEN}✓ No hardcoded secrets detected${NC}"
fi

# 2. Dependency Vulnerability Check
print_section "📦 DEPENDENCY VULNERABILITIES"

if command -v pip-audit &> /dev/null; then
    echo "Running pip-audit..."
    if pip-audit --desc 2>/dev/null | grep -q "found 0 vulnerabilities"; then
        echo -e "${GREEN}✓ No known vulnerabilities in dependencies${NC}"
    else
        VULN_COUNT=$(pip-audit 2>/dev/null | grep -c "^[[:space:]]*[a-zA-Z]" || true)
        echo -e "${YELLOW}⚠ Found $VULN_COUNT vulnerable dependencies${NC}"
        ((TOTAL_ISSUES+=$VULN_COUNT))
    fi
else
    echo -e "${YELLOW}⚠ pip-audit not installed${NC}"
    echo "Install with: pip install pip-audit"
fi

# 3. Python Security Analysis
print_section "🐍 PYTHON CODE SECURITY"

if command -v bandit &> /dev/null; then
    echo "Running bandit security analysis..."
    BANDIT_RESULT=$(bandit -r app/ -f json 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    results = data.get('results', [])
    high = len([r for r in results if r['issue_severity'] == 'HIGH'])
    medium = len([r for r in results if r['issue_severity'] == 'MEDIUM'])
    low = len([r for r in results if r['issue_severity'] == 'LOW'])
    print(f'{high},{medium},{low}')
except:
    print('0,0,0')
" 2>/dev/null)
    
    IFS=',' read -r HIGH MEDIUM LOW <<< "$BANDIT_RESULT"
    
    if [ "$HIGH" -gt 0 ]; then
        echo -e "${RED}❌ Found $HIGH high severity issues${NC}"
        ((CRITICAL_ISSUES+=$HIGH))
        ((TOTAL_ISSUES+=$HIGH))
    fi
    
    if [ "$MEDIUM" -gt 0 ]; then
        echo -e "${YELLOW}⚠ Found $MEDIUM medium severity issues${NC}"
        ((TOTAL_ISSUES+=$MEDIUM))
    fi
    
    if [ "$LOW" -gt 0 ]; then
        echo -e "${BLUE}ℹ Found $LOW low severity issues${NC}"
    fi
    
    if [ "$HIGH" -eq 0 ] && [ "$MEDIUM" -eq 0 ] && [ "$LOW" -eq 0 ]; then
        echo -e "${GREEN}✓ No security issues found by bandit${NC}"
    fi
else
    echo -e "${YELLOW}⚠ bandit not installed${NC}"
    echo "Install with: pip install bandit"
fi

# 4. File Permission Check
print_section "🔐 FILE PERMISSIONS"

echo "Checking for insecure file permissions..."
PERM_ISSUES=0

for file in $(find . -type f -name "*.sh" -o -name "*.py" 2>/dev/null | grep -v ".git"); do
    if [ -f "$file" ]; then
        PERMS=$(stat -c %a "$file" 2>/dev/null || stat -f %A "$file" 2>/dev/null)
        if [ "$PERMS" = "777" ]; then
            echo -e "${RED}❌ $file has insecure permissions (777)${NC}"
            ((PERM_ISSUES++))
            ((TOTAL_ISSUES++))
        fi
    fi
done

if [ $PERM_ISSUES -eq 0 ]; then
    echo -e "${GREEN}✓ No insecure file permissions found${NC}"
fi

# 5. Docker Security Check
print_section "🐳 DOCKER SECURITY"

if [ -f "Dockerfile" ]; then
    echo "Checking Dockerfile..."
    
    # Check for running as root
    if ! grep -q "USER" Dockerfile; then
        echo -e "${YELLOW}⚠ Dockerfile doesn't specify a non-root USER${NC}"
        ((TOTAL_ISSUES++))
    else
        echo -e "${GREEN}✓ Dockerfile specifies a USER${NC}"
    fi
    
    # Check for latest tag
    if grep -q "FROM.*:latest" Dockerfile; then
        echo -e "${YELLOW}⚠ Using 'latest' tag in FROM instruction${NC}"
        ((TOTAL_ISSUES++))
    else
        echo -e "${GREEN}✓ Using specific version tags${NC}"
    fi
fi

# 6. Kubernetes Security Check
print_section "☸️ KUBERNETES SECURITY"

if [ -d "charts" ]; then
    echo "Checking Kubernetes manifests..."
    
    # Check for security contexts
    if grep -r "securityContext" charts/ > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Security contexts defined${NC}"
    else
        echo -e "${YELLOW}⚠ No security contexts found in Helm charts${NC}"
        ((TOTAL_ISSUES++))
    fi
    
    # Check for resource limits
    if grep -r "resources:" charts/ | grep -q "limits"; then
        echo -e "${GREEN}✓ Resource limits defined${NC}"
    else
        echo -e "${YELLOW}⚠ No resource limits found${NC}"
        ((TOTAL_ISSUES++))
    fi
fi

# 7. Git Security Check
print_section "📝 GIT SECURITY"

echo "Checking git history for secrets..."

# Check if git-secrets is installed
if command -v git-secrets &> /dev/null; then
    if git secrets --scan 2>&1 | grep -q "error"; then
        echo -e "${RED}❌ git-secrets found potential issues${NC}"
        ((TOTAL_ISSUES++))
    else
        echo -e "${GREEN}✓ git-secrets scan passed${NC}"
    fi
else
    echo -e "${YELLOW}⚠ git-secrets not installed${NC}"
    echo "Install from: https://github.com/awslabs/git-secrets"
fi

# Summary
print_section "📊 SECURITY SCAN SUMMARY"

if [ $CRITICAL_ISSUES -gt 0 ]; then
    echo -e "${RED}Critical Issues: $CRITICAL_ISSUES${NC}"
fi

echo -e "Total Issues Found: $TOTAL_ISSUES"

if [ $TOTAL_ISSUES -eq 0 ]; then
    echo -e "${GREEN}✅ Security scan completed successfully with no issues!${NC}"
    exit 0
elif [ $CRITICAL_ISSUES -gt 0 ]; then
    echo -e "${RED}❌ Critical security issues found. Please fix before deployment.${NC}"
    exit 1
else
    echo -e "${YELLOW}⚠ Non-critical issues found. Review and fix as needed.${NC}"
    exit 0
fi