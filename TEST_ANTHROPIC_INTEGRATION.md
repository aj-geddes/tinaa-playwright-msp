# Testing TINAA's Anthropic Integration

This guide provides comprehensive instructions for testing TINAA's Anthropic AI integration.

## Overview

TINAA integrates with Anthropic's Claude AI to provide intelligent test generation, code analysis, and problem-solving capabilities. The integration includes:

1. **Settings API** - Configure and manage Anthropic credentials
2. **AI Manager** - Handle AI provider initialization and requests
3. **Internal Problem Solving** - AI-powered assistance for testing challenges
4. **Test Generation** - Create comprehensive test playbooks using AI

## Prerequisites

1. TINAA must be running (Docker or Kubernetes)
2. Valid Anthropic API key (get one at https://console.anthropic.com/)
3. Python 3.8+ with httpx installed

## Quick Start

### 1. Install Dependencies

```bash
pip install httpx
```

### 2. Configure Anthropic

Run the configuration script:

```bash
python configure_anthropic.py
```

This will:
- Check if TINAA is running
- Prompt for your Anthropic API key
- Test the credentials
- Save the configuration

### 3. Test the Integration

Run the test suite:

```bash
python test_anthropic_integration.py
```

This will test:
1. Health check endpoint
2. Provider status
3. Credentials configuration
4. Anthropic API connection
5. MCP integration info

## Manual Testing

### Check Health Status

```bash
curl http://localhost:8080/health
```

### Check Provider Status

```bash
curl http://localhost:8080/api/v1/settings/provider-status
```

### Test Anthropic Connection

```bash
curl -X POST http://localhost:8080/api/v1/settings/test-credential \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "anthropic",
    "config": {
      "apiKey": "YOUR_API_KEY",
      "baseUrl": "https://api.anthropic.com",
      "defaultModel": "claude-3-sonnet-20240229"
    }
  }'
```

## Testing AI Features

### 1. Via MCP Server

The `internal_problem_solving` endpoint is available through the MCP server:

```bash
# Start MCP server
python app/tinaa_mcp_server.py

# Use an MCP client to call:
# - internal_problem_solving
# - collaborative_code_review
# - start_collaborative_session
```

### 2. Via HTTP API

Test AI-powered features through the HTTP API:

```bash
# Create a project from URL with AI analysis
curl -X POST http://localhost:8080/api/workspace/projects/from-url \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "name": "AI Test Project"
  }'
```

## Troubleshooting

### TINAA Not Running

```bash
# Check Docker
docker ps | grep tinaa

# Check Kubernetes
kubectl get pods -n tinaa

# Check logs
docker logs tinaa-app
# or
kubectl logs -n tinaa deployment/tinaa-app
```

### Anthropic Connection Failed

1. Verify API key is correct
2. Check network connectivity to api.anthropic.com
3. Ensure API key has proper permissions
4. Check TINAA logs for detailed errors

### Configuration Not Persisting

If using Kubernetes, ensure secrets are properly created:

```bash
kubectl get secrets -n tinaa | grep anthropic
kubectl describe secret tinaa-anthropic-secret -n tinaa
```

## API Endpoints Reference

### Settings API

- `GET /api/v1/settings/credentials` - Get current configuration
- `POST /api/v1/settings/credentials` - Save credentials
- `POST /api/v1/settings/test-credential` - Test credentials
- `GET /api/v1/settings/provider-status` - Get provider status

### AI Features (via MCP)

- `internal_problem_solving` - Get AI assistance for testing problems
- `collaborative_code_review` - AI-powered code review
- `start_collaborative_session` - Start interactive test design session
- `answer_discovery_questions` - Process requirements and generate tests

## Environment Variables

TINAA supports these environment variables for Anthropic:

```bash
ANTHROPIC_API_KEY=your-api-key
ANTHROPIC_BASE_URL=https://api.anthropic.com
ANTHROPIC_DEFAULT_MODEL=claude-3-sonnet-20240229
```

## Security Notes

1. API keys are stored as Kubernetes secrets (encrypted)
2. Keys are never logged or exposed in responses
3. All API communications use HTTPS
4. Credentials are isolated per namespace

## Next Steps

After successful configuration:

1. Test AI-powered playbook generation
2. Use collaborative test design features
3. Try the problem-solving assistant
4. Explore code review capabilities

## Support

For issues or questions:
1. Check TINAA logs
2. Review the troubleshooting section
3. Consult the API documentation
4. Contact support with error details