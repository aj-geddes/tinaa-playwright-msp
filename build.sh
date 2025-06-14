#!/bin/bash
# Simple build and test script for tinaa-playwright-msp

echo "=== Building tinaa-playwright-msp container ==="
docker-compose build --no-cache

echo "=== Starting container ==="
docker-compose up -d

echo "=== Container logs ==="
sleep 3
docker-compose logs

echo "=== Build completed ==="
echo "Container is running with name: tinaa-playwright-msp and image: tinaa-playwright-msp:latest"
echo "Container will shut down automatically when Claude Desktop closes."
echo "To manually stop it: docker-compose down"
