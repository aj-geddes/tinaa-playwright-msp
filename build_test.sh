#!/bin/bash
echo "Building tinaa-playwright-msp Docker image..."
docker build -t tinaa-playwright-msp .

echo "Running container to verify it works..."
docker run -it --rm --name tinaa-test tinaa-playwright-msp
