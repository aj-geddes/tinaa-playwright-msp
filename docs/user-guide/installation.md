# Installation Guide

This guide provides detailed instructions for installing TINAA (Testing Intelligence Network Automation Assistant).

## Prerequisites

- Node.js 18+ or Docker
- Git (for source installation)
- Supported OS: Windows, macOS, Linux

## Installation Methods

### Method 1: Docker (Recommended)

```bash
docker pull tinaa/tinaa:latest
docker run -p 8765:8765 tinaa/tinaa:latest
```

### Method 2: npm Package

```bash
npm install -g @tinaa/cli
```

### Method 3: Source Installation

```bash
git clone https://github.com/aj-geddes/tinaa-playwright-msp.git
cd tinaa-playwright-msp
npm install
npm run build
```

## Verification

Verify your installation:

```bash
tinaa --version
```

## Next Steps

- [Getting Started Guide](getting-started.md)
- [Quick Start Guide](../QUICK_START.md)
- [User Guide](../USER_GUIDE.md)

## Troubleshooting

For installation issues, see the [Troubleshooting Guide](../TROUBLESHOOTING.md).