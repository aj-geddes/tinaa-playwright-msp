#!/bin/bash
# This script checks the installed FastMCP package structure in a temporary container

# Create a temporary Dockerfile to explore the FastMCP package
cat > explore_fastmcp.dockerfile << 'EOF'
FROM mcr.microsoft.com/playwright:v1.46.1-jammy

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install fastmcp==2.8.0

CMD ["python3", "-c", "import fastmcp; print('FastMCP dir:', dir(fastmcp)); import inspect; import sys; print('FastMCP file:', inspect.getfile(fastmcp)); print('Python version:', sys.version)"]
EOF

# Build and run the temporary container
docker build -t fastmcp-check -f explore_fastmcp.dockerfile .
docker run --rm fastmcp-check
