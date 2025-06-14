# Docker Image Usage Guide

TINAA provides pre-built Docker images through GitHub Container Registry for easy deployment.

## Available Images

- **Latest stable**: `ghcr.io/aj-geddes/tinaa-playwright-msp:latest`
- **Specific version**: `ghcr.io/aj-geddes/tinaa-playwright-msp:v1.0.0`
- **SHA-based**: `ghcr.io/aj-geddes/tinaa-playwright-msp:sha-<commit>`

## Quick Start

### Using Docker Compose (Recommended)

1. Download the production docker-compose file:
```bash
wget https://raw.githubusercontent.com/aj-geddes/tinaa-playwright-msp/main/docker-compose.prod.yml
```

2. Start the service:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

3. Verify it's running:
```bash
curl http://localhost:8765/health
```

### Using Docker Run

```bash
# Pull the latest image
docker pull ghcr.io/aj-geddes/tinaa-playwright-msp:latest

# Run the container
docker run -d \
  --name tinaa-playwright-msp \
  -p 8765:8765 \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd):/mnt/workspace \
  --cap-add SYS_ADMIN \
  ghcr.io/aj-geddes/tinaa-playwright-msp:latest
```

## Configuration

### Environment Variables

- `PYTHONUNBUFFERED=1` - Ensures immediate output
- `PYTHONPATH=/app` - Python module path
- `PLAYWRIGHT_BROWSERS_PATH=/ms-playwright` - Browser installation path
- `TINAA_MODE=http` - Operation mode (http or mcp)

### Volumes

- `/app/logs` - Application logs
- `/mnt/workspace` - Working directory for test files

### Ports

- `8765` - HTTP API and WebSocket endpoint

## Building Custom Images

If you need to build a custom image:

```bash
# Clone the repository
git clone https://github.com/aj-geddes/tinaa-playwright-msp.git
cd tinaa-playwright-msp

# Build the image
docker build -t my-custom-tinaa .

# Run your custom image
docker run -d -p 8765:8765 my-custom-tinaa
```

## Multi-Architecture Support

The pre-built images support multiple architectures:
- `linux/amd64` (Intel/AMD)
- `linux/arm64` (Apple Silicon, ARM servers)

Docker will automatically pull the correct architecture for your system.

## Updating

To get the latest version:

```bash
# Pull the latest image
docker pull ghcr.io/aj-geddes/tinaa-playwright-msp:latest

# Restart with new image
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

## Troubleshooting

### Permission Issues

If you encounter permission issues:

```bash
# Run with privileged mode (less secure)
docker run --privileged -d -p 8765:8765 ghcr.io/aj-geddes/tinaa-playwright-msp:latest
```

### Browser Issues

If browsers fail to launch:

```bash
# Check browser installation
docker exec tinaa-playwright-msp playwright install chromium
```

### Network Issues

For network connectivity problems:

```bash
# Run with host network
docker run --network host -d ghcr.io/aj-geddes/tinaa-playwright-msp:latest
```

## Security Considerations

- The container requires `SYS_ADMIN` capability for browser automation
- Always run with minimal required privileges
- Use volume mounts carefully to avoid exposing sensitive data
- Consider using read-only mounts where possible

## Support

- [GitHub Issues](https://github.com/aj-geddes/tinaa-playwright-msp/issues)
- [Documentation](https://aj-geddes.github.io/tinaa-playwright-msp)
- [Discord Community](https://discord.gg/tinaa-community)