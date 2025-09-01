#!/bin/bash
# Script to apply AI integration updates to TINAA Helm deployment

echo "Applying AI integration updates to TINAA Helm deployment..."

# Get the pod name
POD_NAME=$(kubectl get pods -n tinaa-testing -l app.kubernetes.io/name=tinaa-playwright-msp -o jsonpath='{.items[0].metadata.name}')

if [ -z "$POD_NAME" ]; then
    echo "Error: Could not find TINAA pod"
    exit 1
fi

echo "Found TINAA pod: $POD_NAME"

# Copy AI integration files to pod
echo "Copying AI integration files to pod..."
kubectl cp app/ai_enhanced_handler.py tinaa-testing/$POD_NAME:/app/app/ai_enhanced_handler.py -c tinaa

# Check if files exist and imports work
echo "Verifying AI integration in pod..."
kubectl exec -n tinaa-testing $POD_NAME -- python -c "
import sys
sys.path.insert(0, '/app/app')

# Check if AI handler is properly imported
try:
    from ai_enhanced_handler import generate_exploratory_insights
    print('✓ AI handler imported successfully')
except Exception as e:
    print(f'✗ Error importing AI handler: {e}')

# Check if AI integration module exists
try:
    from ai_integration import AIManager
    print('✓ AI integration module imported successfully')
except Exception as e:
    print(f'✗ Error importing AI integration: {e}')

# Check environment variables
import os
api_key = os.getenv('TINAA_ANTHROPIC_API_KEY', '')
if api_key:
    print(f'✓ Anthropic API key found (length: {len(api_key)})')
else:
    print('✗ Anthropic API key not found')
"

# Test AI functionality
echo "Testing AI functionality..."
kubectl exec -n tinaa-testing $POD_NAME -- python -c "
import asyncio
import sys
sys.path.insert(0, '/app/app')

async def test_ai():
    try:
        from ai_enhanced_handler import get_ai_manager
        ai = await get_ai_manager()
        print(f'✓ AI Manager initialized with providers: {list(ai.providers.keys())}')
        print(f'✓ Active provider: {ai.active_provider}')
        
        # Test a simple completion
        if ai.active_provider:
            result = await ai.chat_completion('Say \"Hello from TINAA AI!\"')
            print(f'✓ AI response: {result[:100]}...')
        else:
            print('✗ No active AI provider')
    except Exception as e:
        print(f'✗ Error testing AI: {e}')

asyncio.run(test_ai())
"

# Restart the pod to ensure changes are loaded
echo "Restarting TINAA deployment..."
kubectl rollout restart deployment/tinaa-tinaa-playwright-msp -n tinaa-testing

# Wait for pod to be ready
echo "Waiting for pod to be ready..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=tinaa-playwright-msp -n tinaa-testing --timeout=120s

# Get new pod name after restart
NEW_POD_NAME=$(kubectl get pods -n tinaa-testing -l app.kubernetes.io/name=tinaa-playwright-msp -o jsonpath='{.items[0].metadata.name}')

# Check logs
echo "Checking TINAA logs after restart..."
kubectl logs -n tinaa-testing $NEW_POD_NAME --tail=30

# Test the API endpoint
echo "Testing exploratory test endpoint with AI..."
kubectl exec -n tinaa-testing $NEW_POD_NAME -- curl -X POST http://localhost:8765/test/exploratory \
  -H "Content-Type: application/json" \
  -d '{
    "action": "test_exploratory",
    "parameters": {
      "url": "https://example.com",
      "focus_area": "general"
    }
  }' | jq .

echo "AI integration update complete!"