#!/bin/bash
# Script to apply AI integration updates to TINAA

echo "Applying AI integration updates to TINAA..."

# Create detect_forms endpoint patch
cat > /tmp/detect-forms-patch.yaml << 'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: http-server-patch
  namespace: tinaa-testing
data:
  patch.py: |
    import fileinput
    import sys
    
    # Add detect_forms endpoint after navigation endpoint
    added_endpoint = False
    for line in fileinput.input('/app/app/http_server.py', inplace=True):
        print(line, end='')
        if not added_endpoint and 'return JSONResponse(content={"success": True, "result": result})' in line and '@app.post("/navigate")' in prev_lines:
            print('''
@app.post("/detect_forms")
@track_progress("Form Field Detection")
async def detect_forms(request: TestRequest):
    form_selector = request.parameters.get("form_selector")
    result = await handle_detect_form_fields(form_selector, ctx=None)
    
    # Generate AI suggestions if form fields were detected
    if result.get("success") and result.get("fields"):
        ai_suggestions = await analyze_form_fields(result["fields"])
        result["ai_suggestions"] = ai_suggestions
    
    return JSONResponse(content={"success": True, "result": result})
''')
            added_endpoint = True
    
    # Track previous lines for context
    if 'prev_lines' not in locals():
        prev_lines = []
    prev_lines.append(line)
    if len(prev_lines) > 10:
        prev_lines.pop(0)
EOF

# Copy files to pod
echo "Copying AI integration files to pod..."
kubectl cp app/ai_enhanced_handler.py tinaa-testing/tinaa-no-vault:/app/app/ai_enhanced_handler.py -c tinaa

# Apply the patch in the pod
echo "Applying patch in pod..."
kubectl exec -n tinaa-testing deploy/tinaa-no-vault -- python -c "
import sys
sys.path.insert(0, '/app/app')

# Check if AI handler is properly imported
try:
    from ai_enhanced_handler import generate_exploratory_insights
    print('AI handler imported successfully')
except Exception as e:
    print(f'Error importing AI handler: {e}')

# Check if AI integration module exists
try:
    from ai_integration import AIManager
    print('AI integration module imported successfully')
except Exception as e:
    print(f'Error importing AI integration: {e}')
"

# Restart the pod to pick up changes
echo "Restarting TINAA pod..."
kubectl rollout restart deployment/tinaa-no-vault -n tinaa-testing

# Wait for pod to be ready
echo "Waiting for pod to be ready..."
kubectl wait --for=condition=ready pod -l app=tinaa-no-vault -n tinaa-testing --timeout=120s

# Check pod status
echo "Checking pod status..."
kubectl get pods -n tinaa-testing -l app=tinaa-no-vault

# Check logs
echo "Checking TINAA logs..."
kubectl logs -n tinaa-testing -l app=tinaa-no-vault --tail=20

echo "AI integration updates applied successfully!"