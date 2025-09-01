#!/bin/bash
# Script to deploy simplified AI integration to TINAA

echo "Deploying simplified AI integration to TINAA..."

# Get the pod name
POD_NAME=$(kubectl get pods -n tinaa-testing -l app.kubernetes.io/name=tinaa-playwright-msp -o jsonpath='{.items[0].metadata.name}')

if [ -z "$POD_NAME" ]; then
    echo "Error: Could not find TINAA pod"
    exit 1
fi

echo "Found TINAA pod: $POD_NAME"

# First check if anthropic module is available
echo "Checking for anthropic module..."
kubectl exec -n tinaa-testing $POD_NAME -c tinaa-playwright-msp -- python -c "
try:
    import anthropic
    print('✓ Anthropic module is available')
except ImportError:
    print('✗ Anthropic module not found - installing...')
    import subprocess
    subprocess.run(['pip', 'install', 'anthropic'], check=True)
    print('✓ Anthropic module installed')
"

# Copy AI integration files to pod
echo "Copying AI integration files..."
kubectl cp app/ai_integration_simple.py tinaa-testing/$POD_NAME:/app/app/ai_integration_simple.py -c tinaa-playwright-msp
kubectl cp app/ai_enhanced_handler.py tinaa-testing/$POD_NAME:/app/app/ai_enhanced_handler.py -c tinaa-playwright-msp

# Verify files were copied and test
echo "Testing AI integration..."
kubectl exec -n tinaa-testing $POD_NAME -c tinaa-playwright-msp -- python -c "
import sys
import os
import asyncio
sys.path.insert(0, '/app/app')

async def test_ai():
    try:
        from ai_integration_simple import AIManager, get_ai_manager
        print('✓ AI integration module imported successfully')
        
        from ai_enhanced_handler import generate_exploratory_insights
        print('✓ AI enhanced handler imported successfully')
        
        # Check for Anthropic credentials
        api_key = os.getenv('TINAA_ANTHROPIC_API_KEY')
        if api_key:
            print(f'✓ Anthropic API key found (length: {len(api_key)})')
            
            # Test AI manager
            ai_manager = await get_ai_manager()
            if ai_manager.active_provider:
                print(f'✓ AI Manager initialized with provider: {ai_manager.active_provider}')
                
                # Test a simple completion
                response = await ai_manager.chat_completion('Say \"Hello from TINAA!\"')
                if response:
                    print(f'✓ AI test successful: {response[:50]}...')
                else:
                    print('✗ AI test failed: No response')
            else:
                print('✗ No active AI provider')
        else:
            print('✗ Anthropic API key not found')
            
    except Exception as e:
        print(f'✗ Error: {e}')
        import traceback
        traceback.print_exc()

asyncio.run(test_ai())
"

# Test the exploratory endpoint
echo "Testing exploratory endpoint with AI..."
kubectl exec -n tinaa-testing $POD_NAME -c tinaa-playwright-msp -- python -c "
import requests
import json

try:
    response = requests.post(
        'http://localhost:8765/test/exploratory',
        json={
            'action': 'test_exploratory',
            'parameters': {
                'url': 'https://example.com',
                'focus_area': 'general'
            }
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        if 'result' in result and 'ai_insights' in result['result']:
            ai_insights = result['result']['ai_insights']
            if ai_insights.get('insights'):
                print('✓ AI insights generated successfully')
                print(f'Provider: {ai_insights.get(\"provider\")}')
                print(f'Insights preview: {ai_insights[\"insights\"][:200]}...')
            else:
                print('✗ No AI insights generated')
                print(f'Error: {ai_insights.get(\"error\")}')
        else:
            print('✗ No ai_insights in response')
    else:
        print(f'✗ Request failed with status: {response.status_code}')
        
except Exception as e:
    print(f'✗ Error testing endpoint: {e}')
"

echo "AI integration deployment complete!"