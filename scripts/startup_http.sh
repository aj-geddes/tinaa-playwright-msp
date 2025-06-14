#!/bin/bash
cd /app
echo "Starting TINAA HTTP server in directory $(pwd)..." > /app/logs/startup_http.log
echo "Python path: $PYTHONPATH" >> /app/logs/startup_http.log
echo "Starting on port 8765..." >> /app/logs/startup_http.log

# Start the HTTP server
exec python /app/app/http_server.py