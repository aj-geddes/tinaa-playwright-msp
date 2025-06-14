FROM mcr.microsoft.com/playwright:v1.46.1-jammy

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Install Python and necessary dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    curl \
    wget \
    ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create symbolic links for python and pip commands
RUN ln -sf /usr/bin/python3 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

# Create workspace directory for mounting local filesystem
RUN mkdir -p /mnt/workspace

# Set up application
WORKDIR /app

# Install Python dependencies with exact version of playwright
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r /app/requirements.txt

# Verify the Playwright installation
RUN python -m playwright install chromium && \
    python -c "from playwright.sync_api import sync_playwright; print('Playwright is working')"

# Create logs directory and app directory if needed
RUN mkdir -p /app/logs && chmod 777 /app/logs
RUN mkdir -p /app/app && touch /app/app/__init__.py

# Copy the application files
COPY . /app/

# Make the script executable
RUN chmod +x /app/minimalist_mcp.py

# Debug check of the FastMCP version and APIs
RUN python -c "import fastmcp; print('FastMCP version:', fastmcp.__version__)" > /app/logs/fastmcp_check.log 2>&1

# Create startup scripts for both MCP and HTTP modes
RUN echo '#!/bin/bash\n\
# Run MCP server directly\n\
cd /app\n\
echo "Starting MCP server in directory $(pwd)..." > /app/logs/startup.log\n\
echo "Python path: $PYTHONPATH" >> /app/logs/startup.log\n\
echo "Available files:" >> /app/logs/startup.log\n\
ls -la >> /app/logs/startup.log\n\
# Execute Python script directly - important to use exec to receive signals\n\
exec python /app/minimalist_mcp.py\n\
' > /app/startup.sh && chmod +x /app/startup.sh

# Copy and make HTTP startup script executable
COPY scripts/startup_http.sh /app/startup_http.sh
RUN chmod +x /app/startup_http.sh

# Create a unified entrypoint that can run either MCP or HTTP mode
RUN echo '#!/bin/bash\n\
if [ "$TINAA_MODE" = "http" ]; then\n\
    echo "Starting TINAA in HTTP mode..."\n\
    exec /app/startup_http.sh\n\
else\n\
    echo "Starting TINAA in MCP mode..."\n\
    exec /app/startup.sh\n\
fi\n\
' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Set working directory to the mounted workspace path
WORKDIR /mnt/workspace

# Run the server with proper signal handling
ENTRYPOINT ["/app/entrypoint.sh"]
