#!/bin/bash
# docker-entrypoint.sh
# Switches between API mode (default) and MCP stdio mode based on TINAA_MODE.
set -euo pipefail

echo "TINAA MSP starting — mode: ${TINAA_MODE:-api}"

if [ "${TINAA_MODE:-api}" = "mcp" ]; then
    echo "Launching FastMCP stdio server..."
    exec tinaa
else
    echo "Launching FastAPI HTTP server on port 8765..."
    exec uvicorn tinaa.api.app:create_app \
        --factory \
        --host 0.0.0.0 \
        --port 8765 \
        --workers "${UVICORN_WORKERS:-1}"
fi
