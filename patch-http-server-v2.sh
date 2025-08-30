#!/bin/bash
# Script to patch HTTP server with AI integration v2

echo "Patching HTTP server with AI integration..."

# Get the pod name
POD_NAME=$(kubectl get pods -n tinaa-testing -l app.kubernetes.io/name=tinaa-playwright-msp -o jsonpath='{.items[0].metadata.name}')

if [ -z "$POD_NAME" ]; then
    echo "Error: Could not find TINAA pod"
    exit 1
fi

echo "Found TINAA pod: $POD_NAME"

# First, create the logs directory if it doesn't exist
echo "Creating logs directory..."
kubectl exec -n tinaa-testing $POD_NAME -c tinaa-playwright-msp -- mkdir -p /app/app/logs

# Create a simple patch to add AI imports after the MCP imports
echo "Adding AI imports to HTTP server..."
kubectl exec -n tinaa-testing $POD_NAME -c tinaa-playwright-msp -- bash -c "
# Add AI imports after MCP imports
sed -i '/get_controller$/a\\
)\\
\\
# AI Integration imports\\
try:\\
    from ai_enhanced_handler import (\\
        generate_exploratory_insights,\\
        analyze_form_fields,\\
        generate_accessibility_insights,\\
        generate_security_insights,\\
        generate_test_report_summary\\
    )\\
    AI_AVAILABLE = True\\
except ImportError as e:\\
    print(f\"AI integration not available: {e}\")\\
    AI_AVAILABLE = False\\
\\
from workspace_manager import WorkspaceManager\\
from settings_api import setup_settings_api\\
\\
# Remove duplicate imports if they exist\\
sed -i \"s/^)$/\" /app/app/http_server.py' /app/app/http_server.py
"

# Now patch the exploratory test endpoint
echo "Patching exploratory test endpoint..."
kubectl exec -n tinaa-testing $POD_NAME -c tinaa-playwright-msp -- python -c "
import re

# Read the file
with open('/app/app/http_server.py', 'r') as f:
    content = f.read()

# Find the exploratory test function
pattern = r'(@app\.post\(\"/test/exploratory\"\).*?return StreamingResponse.*?\n)'
match = re.search(pattern, content, re.DOTALL)

if match:
    func_content = match.group(0)
    
    # Check if AI code already exists
    if 'generate_exploratory_insights' not in func_content:
        # Find where to insert the AI code (before the final progress update)
        insert_pattern = r'(        if client_id:\n            await manager\.send_progress\(client_id, {\"phase\": \"complete\", \"progress\": 100}\)\n)'
        
        ai_code = '''        
        # Generate AI insights if available
        if 'AI_AVAILABLE' in globals() and AI_AVAILABLE and result.get(\"success\") and not result.get(\"error\"):
            if client_id:
                await manager.send_progress(client_id, {\"phase\": \"analyzing\", \"progress\": 50})
                await manager.send_message(client_id, \"Generating AI insights...\", \"info\")
            
            try:
                ai_insights = await generate_exploratory_insights(
                    url=url,
                    title=result.get(\"title\", \"\"),
                    screenshot_data=result.get(\"initial_screenshot\"),
                    focus_area=focus_area
                )
                result[\"ai_insights\"] = ai_insights
                
                if client_id:
                    if ai_insights.get(\"insights\"):
                        await manager.send_message(client_id, \"AI insights generated successfully\", \"success\")
                    else:
                        await manager.send_message(client_id, \"AI insights not available\", \"warning\")
            except Exception as e:
                print(f\"Error generating AI insights: {e}\")
                result[\"ai_insights\"] = {\"error\": str(e)}
        
'''
        
        new_func = re.sub(insert_pattern, ai_code + r'\1', func_content)
        content = content.replace(func_content, new_func)
        
        # Write the updated content
        with open('/app/app/http_server.py', 'w') as f:
            f.write(content)
        
        print('✓ Exploratory endpoint patched successfully')
    else:
        print('✓ AI code already present in exploratory endpoint')
else:
    print('✗ Could not find exploratory test endpoint')
"

# Restart the pod to apply changes
echo "Restarting TINAA pod..."
kubectl delete pod $POD_NAME -n tinaa-testing

# Wait for new pod to be ready
echo "Waiting for new pod..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=tinaa-playwright-msp -n tinaa-testing --timeout=120s

# Get new pod name
NEW_POD_NAME=$(kubectl get pods -n tinaa-testing -l app.kubernetes.io/name=tinaa-playwright-msp -o jsonpath='{.items[0].metadata.name}')

# Wait a bit more for services to start
sleep 10

# Test the endpoint
echo "Testing exploratory endpoint with AI..."
kubectl exec -n tinaa-testing $NEW_POD_NAME -c tinaa-playwright-msp -- curl -s -X POST http://localhost:8765/test/exploratory \
  -H "Content-Type: application/json" \
  -d '{
    "action": "test_exploratory",
    "parameters": {
      "url": "https://example.com",
      "focus_area": "general"
    }
  }' | jq -C '.result.ai_insights | if . then (if .insights then "✓ AI insights generated!\nProvider: " + .provider + "\nInsights: " + (.insights | .[0:300]) + "..." else "✗ No insights: " + .error end) else "✗ No AI insights in response" end' -r

echo "Done!"