#!/bin/bash
# Script to rebuild TINAA with Vault integration fixes

echo "🔨 Building Docker image with Vault integration fixes..."

# Build the Docker image
docker build -t tinaa-playwright-msp:vault-fix .

# Tag for local registry or Docker Hub (adjust as needed)
docker tag tinaa-playwright-msp:vault-fix ghcr.io/aj-geddes/tinaa-playwright-msp:vault-fix

echo "📤 Pushing image to registry..."
# Push to registry (requires authentication)
docker push ghcr.io/aj-geddes/tinaa-playwright-msp:vault-fix

echo "🚀 Updating Kubernetes deployment..."
# Update the deployment to use the new image
kubectl set image deployment/tinaa-tinaa-playwright-msp \
  tinaa-playwright-msp=ghcr.io/aj-geddes/tinaa-playwright-msp:vault-fix \
  -n tinaa-testing

echo "⏳ Waiting for rollout to complete..."
kubectl rollout status deployment/tinaa-tinaa-playwright-msp -n tinaa-testing

echo "✅ Deployment updated! TINAA should now have access to Vault secrets."
echo ""
echo "To verify:"
echo "1. Check pod logs: kubectl logs -n tinaa-testing -l app.kubernetes.io/name=tinaa-playwright-msp --tail=50"
echo "2. Test Anthropic: curl -X POST http://localhost:8765/test/exploratory -H 'Content-Type: application/json' -d '{\"action\":\"exploratory\",\"parameters\":{\"url\":\"https://example.com\",\"prompt\":\"Test Anthropic integration\"}}'"