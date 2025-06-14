# Installation Guide

This guide provides detailed instructions for installing TINAA (Testing Intelligence Network Automation Assistant).

## Prerequisites

- Docker (recommended) or Python 3.8+
- Git (for source installation)
- Supported OS: Windows, macOS, Linux
- Minimum 4GB RAM, 2GB disk space

## Installation Methods

### Method 1: Pre-built Docker Image (Recommended)

**Fastest setup using pre-built images from GitHub Container Registry**

```bash
# Download the production docker-compose file
curl -O https://raw.githubusercontent.com/aj-geddes/tinaa-playwright-msp/main/docker-compose.prod.yml

# Start TINAA with pre-built image
docker-compose -f docker-compose.prod.yml up -d

# Verify installation
curl http://localhost:8765/health
```

The image `ghcr.io/aj-geddes/tinaa-playwright-msp:latest` will be automatically pulled.

**Using specific versions:**
```bash
# Pull a specific version
docker pull ghcr.io/aj-geddes/tinaa-playwright-msp:v1.0.0

# Run with version tag
docker run -p 8765:8765 ghcr.io/aj-geddes/tinaa-playwright-msp:v1.0.0
```

### Method 2: Build from Source with Docker

**For development and customization**

```bash
# Clone repository
git clone https://github.com/aj-geddes/tinaa-playwright-msp.git
cd tinaa-playwright-msp

# Build and run
docker-compose up -d

# For HTTP mode
docker-compose -f docker-compose.http.yml up -d
```

### Method 3: Local Python Installation

**For direct development access**

```bash
# Clone repository
git clone https://github.com/aj-geddes/tinaa-playwright-msp.git
cd tinaa-playwright-msp

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Start TINAA
python app/http_server.py
```

### Method 4: Claude Desktop Integration

**For AI assistant integration**

Add to Claude Desktop settings:
```json
{
  "mcpServers": {
    "tinaa-playwright": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "ghcr.io/aj-geddes/tinaa-playwright-msp:latest"]
    }
  }
}
```

## Verification

Verify your installation:

```bash
# Check health endpoint
curl http://localhost:8765/health
# Expected: {"status":"healthy","timestamp":"..."}

# Test browser connectivity
curl -X POST http://localhost:8765/test/connectivity
# Expected: {"success":true,"result":"Browser started successfully."}

# Check Docker container (if using Docker)
docker ps | grep tinaa
```

## Configuration

### Environment Variables

Create a `.env` file for custom configuration:

```bash
# TINAA Configuration
TINAA_MODE=http                    # 'http' or 'mcp'
PLAYWRIGHT_BROWSERS_PATH=/ms-playwright # Browser location
LOG_LEVEL=INFO                     # DEBUG, INFO, WARNING, ERROR
MAX_CONCURRENT_TESTS=3             # Parallel test limit
DEFAULT_TIMEOUT=30000              # Default timeout (ms)
SCREENSHOT_ON_FAILURE=true         # Auto-capture on errors
```

### Docker Compose Configuration

Customize `docker-compose.prod.yml` for your environment:

```yaml
version: '3.8'

services:
  tinaa-http:
    image: ghcr.io/aj-geddes/tinaa-playwright-msp:latest
    container_name: tinaa-playwright-msp-http
    command: ["python", "/app/app/http_server.py"]
    ports:
      - "8765:8765"  # Change port if needed
    environment:
      - PYTHONUNBUFFERED=1
      - PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
      - TINAA_MODE=http
      - LOG_LEVEL=INFO  # Adjust logging level
    volumes:
      - ./logs:/app/logs
      - ${PWD}:/mnt/workspace
    restart: unless-stopped
    # Resource limits (optional)
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '0.5'
          memory: 1G
```

## Updating TINAA

### Updating Pre-built Image

```bash
# Pull latest image
docker pull ghcr.io/aj-geddes/tinaa-playwright-msp:latest

# Restart with new image
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

### Updating from Source

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose build
docker-compose up -d
```

## Next Steps

- [Getting Started Guide](getting-started.md)
- [Quick Start Guide](../QUICK_START.md)
- [User Guide](../USER_GUIDE.md)

## Troubleshooting

For installation issues, see the [Troubleshooting Guide](../TROUBLESHOOTING.md).