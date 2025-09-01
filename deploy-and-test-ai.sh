#!/bin/bash
# Complete AI deployment and testing script

echo "Complete AI deployment for TINAA..."

# Get the pod name
POD_NAME=$(kubectl get pods -n tinaa-testing -l app.kubernetes.io/name=tinaa-playwright-msp -o jsonpath='{.items[0].metadata.name}')

if [ -z "$POD_NAME" ]; then
    echo "Error: Could not find TINAA pod"
    exit 1
fi

echo "Found TINAA pod: $POD_NAME"

# Step 1: Install anthropic module
echo "Step 1: Installing anthropic module..."
kubectl exec -n tinaa-testing $POD_NAME -c tinaa-playwright-msp -- pip install anthropic --quiet

# Step 2: Copy AI files
echo "Step 2: Copying AI files..."
kubectl cp app/ai_integration_simple.py tinaa-testing/$POD_NAME:/app/app/ai_integration_simple.py -c tinaa-playwright-msp
kubectl cp app/ai_enhanced_handler.py tinaa-testing/$POD_NAME:/app/app/ai_enhanced_handler.py -c tinaa-playwright-msp

# Step 3: Create logs directory
echo "Step 3: Creating logs directory..."
kubectl exec -n tinaa-testing $POD_NAME -c tinaa-playwright-msp -- mkdir -p /app/app/logs

# Step 4: Copy updated http_server.py (with AI integration)
echo "Step 4: Copying updated http_server.py..."
kubectl cp app/http_server.py tinaa-testing/$POD_NAME:/app/app/http_server.py -c tinaa-playwright-msp

# Step 5: Verify AI is working
echo "Step 5: Verifying AI integration..."
kubectl exec -n tinaa-testing $POD_NAME -c tinaa-playwright-msp -- python -c "
import sys
import asyncio
sys.path.insert(0, '/app/app')

async def test():
    from ai_integration_simple import get_ai_manager
    ai = await get_ai_manager()
    if ai.active_provider:
        print('✓ AI Manager active with provider:', ai.active_provider)
        response = await ai.chat_completion('Say hello')
        if response:
            print('✓ AI test successful')
        else:
            print('✗ AI test failed')
    else:
        print('✗ No active AI provider')

asyncio.run(test())
"

# Step 6: Restart the HTTP server process
echo "Step 6: Restarting HTTP server..."
kubectl exec -n tinaa-testing $POD_NAME -c tinaa-playwright-msp -- bash -c "
# Kill the current http server
pkill -f 'python.*http_server' || true
sleep 2

# Start it again in background
cd /app && nohup python -m app.http_server > /app/app/logs/http_server.log 2>&1 &
sleep 5

# Check if it's running
if pgrep -f 'python.*http_server' > /dev/null; then
    echo '✓ HTTP server restarted successfully'
else
    echo '✗ HTTP server failed to start'
    tail -20 /app/app/logs/http_server.log
fi
"

# Step 7: Test the exploratory endpoint
echo "Step 7: Testing exploratory endpoint with AI..."
sleep 5  # Give server time to fully start

kubectl exec -n tinaa-testing $POD_NAME -c tinaa-playwright-msp -- python -c "
import requests
import json

url = 'http://localhost:8765/test/exploratory'
data = {
    'action': 'test_exploratory',
    'parameters': {
        'url': 'https://example.com',
        'focus_area': 'general'
    }
}

try:
    print('Sending request to:', url)
    response = requests.post(url, json=data, timeout=30)
    
    if response.status_code == 200:
        result = response.json()
        if 'result' in result and 'ai_insights' in result['result']:
            ai_insights = result['result']['ai_insights']
            if ai_insights and ai_insights.get('insights'):
                print('✓ AI INSIGHTS GENERATED SUCCESSFULLY!')
                print('Provider:', ai_insights.get('provider'))
                print('Focus area:', ai_insights.get('focus_area'))
                print('\\nInsights preview:')
                print(ai_insights['insights'][:500] + '...')
            else:
                print('✗ No AI insights generated')
                if ai_insights:
                    print('Error:', ai_insights.get('error'))
        else:
            print('✗ No ai_insights field in response')
            print('Response keys:', list(result.get('result', {}).keys()))
    else:
        print(f'✗ Request failed with status: {response.status_code}')
        print('Response:', response.text[:500])
        
except Exception as e:
    print(f'✗ Error: {e}')
    import traceback
    traceback.print_exc()
"

echo "AI deployment complete!"