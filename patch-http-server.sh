#!/bin/bash
# Script to patch HTTP server with AI integration

echo "Patching HTTP server with AI integration..."

# Get the pod name
POD_NAME=$(kubectl get pods -n tinaa-testing -l app.kubernetes.io/name=tinaa-playwright-msp -o jsonpath='{.items[0].metadata.name}')

if [ -z "$POD_NAME" ]; then
    echo "Error: Could not find TINAA pod"
    exit 1
fi

echo "Found TINAA pod: $POD_NAME"

# Create a patch file
echo "Creating patch..."
kubectl exec -n tinaa-testing $POD_NAME -c tinaa-playwright-msp -- bash -c "cat > /tmp/http_server_patch.py << 'EOF'
import sys

# Read the http_server.py file
with open('/app/app/http_server.py', 'r') as f:
    content = f.read()

# Check if AI imports already exist
if 'from ai_enhanced_handler import' not in content:
    # Find the line after the mcp_handler imports
    import_pos = content.find(')\n\nfrom workspace_manager')
    if import_pos > 0:
        # Insert the AI imports
        ai_imports = ''')\n\ntry:\n    from ai_enhanced_handler import (\n        generate_exploratory_insights,\n        analyze_form_fields,\n        generate_accessibility_insights,\n        generate_security_insights,\n        generate_test_report_summary\n    )\n    AI_AVAILABLE = True\nexcept ImportError:\n    print(\"AI integration not available\")\n    AI_AVAILABLE = False\n\nfrom workspace_manager'''
        
        content = content[:import_pos] + ai_imports + content[import_pos+2:]
        
        # Also update the exploratory test endpoint
        exploratory_start = content.find('@app.post(\"/test/exploratory\")')
        if exploratory_start > 0:
            # Find the end of this function
            func_end = content.find('return StreamingResponse(stream_test(), media_type=\"application/json\")', exploratory_start)
            if func_end > 0:
                # Find where to insert AI code
                progress_100 = content.rfind('await manager.send_progress(client_id, {\"phase\": \"complete\", \"progress\": 100})', exploratory_start, func_end)
                if progress_100 > 0:
                    # Insert AI code before progress 100
                    ai_code = '''
        if client_id:
            await manager.send_progress(client_id, {\"phase\": \"analyzing\", \"progress\": 50})
            await manager.send_message(client_id, \"Generating AI insights...\", \"info\")
        
        # Generate AI insights if available and test was successful
        if AI_AVAILABLE and result.get(\"success\") and not result.get(\"error\"):
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
                    content = content[:progress_100] + ai_code + content[progress_100:]
        
        # Write the updated content
        with open('/app/app/http_server.py', 'w') as f:
            f.write(content)
        
        print('✓ HTTP server patched successfully')
    else:
        print('✗ Could not find import position')
else:
    print('✓ AI imports already present')

EOF"

# Run the patch
echo "Applying patch..."
kubectl exec -n tinaa-testing $POD_NAME -c tinaa-playwright-msp -- python /tmp/http_server_patch.py

# Restart the HTTP server by killing the process (it will auto-restart)
echo "Restarting HTTP server..."
kubectl exec -n tinaa-testing $POD_NAME -c tinaa-playwright-msp -- pkill -f "python.*http_server" || true

# Wait a moment for restart
sleep 5

# Test the endpoint
echo "Testing exploratory endpoint with AI..."
kubectl exec -n tinaa-testing $POD_NAME -c tinaa-playwright-msp -- curl -s -X POST http://localhost:8765/test/exploratory \
  -H "Content-Type: application/json" \
  -d '{
    "action": "test_exploratory",
    "parameters": {
      "url": "https://example.com",
      "focus_area": "general"
    }
  }' | jq -r '.result.ai_insights | if . then (if .insights then "✓ AI insights generated successfully\nProvider: \(.provider)\nInsights preview: \(.insights | .[0:200])..." else "✗ No insights: \(.error)" end) else "✗ No AI insights in response" end'

echo "HTTP server patching complete!"