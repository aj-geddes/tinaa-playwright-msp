#!/bin/bash
# TINAA HTTP Server Startup Script with Vault Integration

# Source all Vault secrets if they exist
if [ -d "/vault/secrets" ]; then
    echo "Loading Vault secrets..."
    for secret in /vault/secrets/*; do
        if [ -f "$secret" ]; then
            echo "  Sourcing: $(basename $secret)"
            source "$secret"
        fi
    done
    echo "Vault secrets loaded successfully"
else
    echo "No Vault secrets directory found, continuing without secrets"
fi

# Change to app directory
cd /app

# Log startup information
echo "Starting TINAA HTTP server in directory $(pwd)..." > /app/logs/startup_http.log
echo "Python path: $PYTHONPATH" >> /app/logs/startup_http.log
echo "Starting on port 8765..." >> /app/logs/startup_http.log

# Log loaded secrets (without exposing values)
echo "Environment check:" >> /app/logs/startup_http.log
[ -n "$TINAA_ANTHROPIC_API_KEY" ] && echo "  ✓ Anthropic API key loaded" >> /app/logs/startup_http.log
[ -n "$TINAA_OPENAI_API_KEY" ] && echo "  ✓ OpenAI API key loaded" >> /app/logs/startup_http.log
[ -n "$TINAA_GIT_PAT" ] && echo "  ✓ Git PAT loaded" >> /app/logs/startup_http.log
[ -n "$TINAA_GIT_APP_ID" ] && echo "  ✓ GitHub App credentials loaded" >> /app/logs/startup_http.log

# Start the HTTP server
exec python /app/app/http_server.py