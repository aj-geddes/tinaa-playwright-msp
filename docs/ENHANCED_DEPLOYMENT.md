# TINAA Enhanced Deployment Guide

This guide covers deploying the enhanced TINAA system with AI integration, collaborative IDE support, and comprehensive workspace management.

## Overview

The enhanced TINAA includes:
- **AI-Powered Collaboration**: Integration with OpenAI, Anthropic, and local LLMs
- **MCP Server**: Exposes TINAA capabilities to LLM-enabled IDEs
- **Enhanced Workspace**: 100GB+ storage for multiple Playwright projects
- **Git Integration**: Secure repository cloning with PAT and GitHub App support
- **Frontend Interface**: React-based UI for activity monitoring and workspace management
- **Collaborative Design**: Interactive test playbook creation with IDE LLMs

## Prerequisites

### Kubernetes Cluster
- Kubernetes 1.19+
- Helm 3.2.0+
- Sufficient storage provisioner
- RBAC enabled for secret management

### Required Secrets
- AI provider API keys
- Git authentication credentials
- Database credentials (if using PostgreSQL)

## Secret Management

### 1. Create AI Provider Secrets

#### OpenAI Secret
```bash
kubectl create secret generic tinaa-openai-secret \
  --from-literal=api-key="your-openai-api-key"
```

#### Anthropic Secret
```bash
kubectl create secret generic tinaa-anthropic-secret \
  --from-literal=api-key="your-anthropic-api-key"
```

### 2. Create Git Authentication Secrets

#### Option A: Personal Access Token (PAT)
```bash
kubectl create secret generic tinaa-git-secret \
  --from-literal=pat-token="your-github-pat" \
  --from-literal=username="your-github-username"
```

#### Option B: GitHub App Authentication
```bash
# First, save your private key to a file
cat > github-app-key.pem << 'EOF'
-----BEGIN RSA PRIVATE KEY-----
Your GitHub App private key here
-----END RSA PRIVATE KEY-----
EOF

kubectl create secret generic tinaa-github-app-secret \
  --from-literal=app-id="your-app-id" \
  --from-literal=installation-id="your-installation-id" \
  --from-file=private-key=github-app-key.pem

# Clean up the key file
rm github-app-key.pem
```

### 3. Create Database Secret (PostgreSQL only)
```bash
kubectl create secret generic tinaa-database-secret \
  --from-literal=password="your-postgres-password"
```

## Deployment Options

### Option 1: Basic Enhanced Deployment

```bash
# Deploy with enhanced features using existing secrets
helm install tinaa ./charts/tinaa-playwright-msp \
  -f ./charts/tinaa-playwright-msp/values-enhanced.yaml \
  --set tinaa.aiProviders.openai.enabled=true \
  --set tinaa.aiProviders.anthropic.enabled=true \
  --set tinaa.git.pat.enabled=true \
  --create-namespace \
  --namespace tinaa-enhanced
```

### Option 2: Full Production Deployment

```yaml
# values-production.yaml
replicaCount: 2

resources:
  limits:
    cpu: 8
    memory: 16Gi
  requests:
    cpu: 4
    memory: 8Gi

tinaa:
  mode: "enhanced"
  
  aiProviders:
    openai:
      enabled: true
      existingSecret: "tinaa-openai-secret"
      defaultModel: "gpt-4"
    
    anthropic:
      enabled: true
      existingSecret: "tinaa-anthropic-secret"
      defaultModel: "claude-3-sonnet-20240229"
  
  git:
    githubApp:
      enabled: true
      existingSecret: "tinaa-github-app-secret"
  
  persistence:
    workspace:
      size: 500Gi
      storageClass: "fast-ssd"
    
    aiCache:
      size: 100Gi
      storageClass: "fast-ssd"

ingress:
  enabled: true
  className: "nginx"
  hosts:
    - host: tinaa.yourdomain.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: tinaa-tls
      hosts:
        - tinaa.yourdomain.com

# Deploy with production values
helm install tinaa ./charts/tinaa-playwright-msp \
  -f values-production.yaml \
  --create-namespace \
  --namespace tinaa-production
```

### Option 3: Development with Local LLM

```yaml
# values-development.yaml
tinaa:
  mode: "enhanced"
  
  aiProviders:
    ollama:
      enabled: true
      baseUrl: "http://ollama.ollama:11434"
      defaultModel: "codellama"
  
  git:
    pat:
      enabled: true
      existingSecret: "tinaa-git-secret"
  
  persistence:
    workspace:
      size: 50Gi
    aiCache:
      enabled: false  # Disable for local development

# Deploy Ollama first
helm repo add ollama https://otwld.github.io/ollama-helm/
helm install ollama ollama/ollama --namespace ollama --create-namespace

# Deploy TINAA
helm install tinaa ./charts/tinaa-playwright-msp \
  -f values-development.yaml \
  --namespace tinaa-dev \
  --create-namespace
```

## IDE Integration Setup

### 1. Configure MCP in Your IDE

For Claude Desktop or other MCP-enabled editors:

```json
{
  "mcpServers": {
    "tinaa": {
      "command": "curl",
      "args": [
        "-X", "POST",
        "http://tinaa.yournamespace:8765/mcp/connect"
      ],
      "env": {}
    }
  }
}
```

### 2. Start Collaborative Session

In your IDE, you can now use TINAA MCP tools:

```typescript
// Start a collaborative test design session
const session = await tinaa.start_collaborative_session({
  project_name: "My Web App Tests",
  project_description: "E-commerce testing suite",
  target_url: "https://myapp.com",
  existing_code_context: "React app with TypeScript"
});

// Answer discovery questions
await tinaa.answer_discovery_questions({
  session_id: session.session_id,
  answers: {
    app_purpose: "Online shopping platform",
    user_journeys: "Browse products, add to cart, checkout",
    browser_support: "Chrome, Firefox, Safari, Mobile",
    auth_methods: "Email/password, Google OAuth, Apple ID",
    success_criteria: "All critical user flows work flawlessly"
  }
});

// Create comprehensive playbook
const playbook = await tinaa.create_comprehensive_playbook({
  session_id: session.session_id,
  playbook_preferences: {
    automation_level: "high",
    test_types: ["functional", "accessibility", "performance"],
    reporting: "detailed"
  }
});
```

## Verification and Testing

### 1. Check Pod Status
```bash
kubectl get pods -n tinaa-enhanced
kubectl logs -f deployment/tinaa-playwright-msp -n tinaa-enhanced
```

### 2. Verify AI Integration
```bash
# Port forward to access TINAA
kubectl port-forward service/tinaa-playwright-msp 8765:8765 -n tinaa-enhanced

# Test AI providers
curl -X POST http://localhost:8765/api/ai/providers/status
```

### 3. Test Git Access
```bash
# Test repository cloning
curl -X POST http://localhost:8765/api/workspace/projects/from-url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com/microsoft/playwright", "name": "playwright-tests"}'
```

### 4. Test Collaborative Session
```bash
# Start a collaborative session via API
curl -X POST http://localhost:8765/mcp/start_collaborative_session \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "Test Project",
    "project_description": "API testing suite"
  }'
```

## Monitoring and Maintenance

### 1. Resource Monitoring
```bash
# Check resource usage
kubectl top pods -n tinaa-enhanced
kubectl top nodes

# Check storage usage
kubectl get pvc -n tinaa-enhanced
```

### 2. AI Provider Health
```bash
# Check AI provider status
kubectl exec -it deployment/tinaa-playwright-msp -n tinaa-enhanced -- \
  python -c "
import asyncio
from app.secrets_manager import secrets_manager
print(asyncio.run(secrets_manager.validate_secrets()))
"
```

### 3. Workspace Management
```bash
# List active projects
curl http://localhost:8765/api/workspace/projects

# Check workspace status
curl http://localhost:8765/api/workspace/status
```

## Troubleshooting

### Common Issues

#### 1. AI Provider Authentication Errors
```bash
# Check secret contents
kubectl get secret tinaa-openai-secret -o yaml
kubectl describe secret tinaa-openai-secret

# Verify secret mounting
kubectl exec deployment/tinaa-playwright-msp -- ls -la /var/run/secrets/
```

#### 2. Git Authentication Failures
```bash
# Test git credentials
kubectl exec deployment/tinaa-playwright-msp -- \
  python -c "
import asyncio
from app.git_auth import git_authenticator
print(asyncio.run(git_authenticator.validate_git_credentials()))
"
```

#### 3. Storage Issues
```bash
# Check PVC status
kubectl describe pvc tinaa-playwright-msp-workspace

# Check storage class
kubectl get storageclass
```

#### 4. MCP Connection Issues
```bash
# Check MCP server status
curl http://localhost:8765/mcp/status

# Test MCP tools
curl -X POST http://localhost:8765/mcp/tools/list
```

### Log Analysis
```bash
# Application logs
kubectl logs deployment/tinaa-playwright-msp -n tinaa-enhanced --tail=100

# AI integration logs
kubectl logs deployment/tinaa-playwright-msp -n tinaa-enhanced | grep "ai_integration"

# Git authentication logs
kubectl logs deployment/tinaa-playwright-msp -n tinaa-enhanced | grep "git_auth"

# MCP server logs
kubectl logs deployment/tinaa-playwright-msp -n tinaa-enhanced | grep "mcp_server"
```

## Scaling and Performance

### Horizontal Scaling
```yaml
# Enable HPA in values
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80
```

### Resource Optimization
```yaml
# Optimize for AI workloads
resources:
  limits:
    cpu: 8
    memory: 16Gi
    nvidia.com/gpu: 1  # If GPU acceleration needed
  requests:
    cpu: 4
    memory: 8Gi

# Use fast storage for AI cache
tinaa:
  persistence:
    aiCache:
      storageClass: "nvme-ssd"
      size: 200Gi
```

## Security Considerations

### 1. Network Policies
```yaml
networkPolicy:
  enabled: true
  ingress:
    - from:
      - namespaceSelector:
          matchLabels:
            name: allowed-namespace
  egress:
    - to: []  # Restrict outbound access as needed
```

### 2. Pod Security
```yaml
podSecurityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000

securityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    add:
      - SYS_ADMIN  # Required for browser automation
    drop:
      - ALL
```

### 3. Secret Rotation
```bash
# Rotate API keys periodically
kubectl create secret generic tinaa-openai-secret-new \
  --from-literal=api-key="new-api-key"

# Update deployment to use new secret
helm upgrade tinaa ./charts/tinaa-playwright-msp \
  --set tinaa.aiProviders.openai.existingSecret=tinaa-openai-secret-new
```

This enhanced deployment provides a comprehensive AI-powered testing platform that can collaborate with IDEs, manage complex testing projects, and provide intelligent guidance throughout the testing lifecycle.