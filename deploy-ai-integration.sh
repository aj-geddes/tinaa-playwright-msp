#!/bin/bash
# Script to deploy AI integration to TINAA

echo "Deploying AI integration to TINAA..."

# Get the pod name
POD_NAME=$(kubectl get pods -n tinaa-testing -l app.kubernetes.io/name=tinaa-playwright-msp -o jsonpath='{.items[0].metadata.name}')

if [ -z "$POD_NAME" ]; then
    echo "Error: Could not find TINAA pod"
    exit 1
fi

echo "Found TINAA pod: $POD_NAME"

# Copy AI integration files to pod
echo "Copying AI integration files..."
kubectl cp app/ai_integration.py tinaa-testing/$POD_NAME:/app/app/ai_integration.py -c tinaa-playwright-msp
kubectl cp app/ai_enhanced_handler.py tinaa-testing/$POD_NAME:/app/app/ai_enhanced_handler.py -c tinaa-playwright-msp

# Verify files were copied
echo "Verifying files..."
kubectl exec -n tinaa-testing $POD_NAME -c tinaa-playwright-msp -- ls -la /app/app/ai_*.py

# Test AI integration
echo "Testing AI integration..."
kubectl exec -n tinaa-testing $POD_NAME -c tinaa-playwright-msp -- python -c "
import sys
sys.path.insert(0, '/app/app')

try:
    from ai_integration import AIManager
    print('✓ AI integration module imported successfully')
    
    from ai_enhanced_handler import generate_exploratory_insights
    print('✓ AI enhanced handler imported successfully')
    
    # Check for Anthropic credentials
    import os
    if os.getenv('TINAA_ANTHROPIC_API_KEY'):
        print('✓ Anthropic API key found')
    else:
        print('✗ Anthropic API key not found')
        
except Exception as e:
    print(f'✗ Error: {e}')
"

# Restart the pod to ensure changes are loaded
echo "Restarting TINAA deployment..."
kubectl rollout restart deployment/tinaa-tinaa-playwright-msp -n tinaa-testing

# Wait for pod to be ready
echo "Waiting for pod to be ready..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=tinaa-playwright-msp -n tinaa-testing --timeout=120s

# Get new pod name
NEW_POD_NAME=$(kubectl get pods -n tinaa-testing -l app.kubernetes.io/name=tinaa-playwright-msp -o jsonpath='{.items[0].metadata.name}')

# Test exploratory endpoint with AI
echo "Testing exploratory endpoint with AI..."
kubectl exec -n tinaa-testing $NEW_POD_NAME -c tinaa-playwright-msp -- curl -X POST http://localhost:8765/test/exploratory \
  -H "Content-Type: application/json" \
  -d '{
    "action": "test_exploratory",
    "parameters": {
      "url": "https://example.com",
      "focus_area": "general"
    }
  }' | jq .result.ai_insights

echo "AI integration deployment complete!"