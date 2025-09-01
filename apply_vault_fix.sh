#!/bin/bash
# Quick fix to apply Vault integration to running TINAA pod

POD_NAME=$(kubectl get pods -n tinaa-testing -l app.kubernetes.io/name=tinaa-playwright-msp -o jsonpath='{.items[0].metadata.name}')

if [ -z "$POD_NAME" ]; then
    echo "❌ No TINAA pod found"
    exit 1
fi

echo "🔧 Applying Vault fix to pod: $POD_NAME"

# Create a wrapper script that sources Vault secrets and restarts the server
kubectl exec -n tinaa-testing $POD_NAME -- bash -c 'cat > /tmp/restart_with_vault.sh << "EOF"
#!/bin/bash
echo "Stopping current HTTP server..."
pkill -f "python /app/app/http_server.py" || true
sleep 2

# Source all Vault secrets
if [ -d "/vault/secrets" ]; then
    echo "Loading Vault secrets..."
    for secret in /vault/secrets/*; do
        if [ -f "$secret" ]; then
            echo "  Sourcing: $(basename $secret)"
            source "$secret"
        fi
    done
    echo "Vault secrets loaded successfully"
    
    # Verify secrets are loaded
    echo "Verification:"
    [ -n "$TINAA_ANTHROPIC_API_KEY" ] && echo "  ✓ Anthropic API key loaded"
    [ -n "$TINAA_OPENAI_API_KEY" ] && echo "  ✓ OpenAI API key loaded"
    [ -n "$TINAA_GIT_PAT" ] && echo "  ✓ Git PAT loaded"
fi

# Start the HTTP server with environment variables
cd /app
exec python /app/app/http_server.py
EOF
chmod +x /tmp/restart_with_vault.sh
'

echo "🚀 Restarting TINAA with Vault secrets..."
kubectl exec -n tinaa-testing $POD_NAME -- nohup /tmp/restart_with_vault.sh > /tmp/restart.log 2>&1 &

echo "⏳ Waiting for server to start..."
sleep 5

# Check if the server is running
kubectl exec -n tinaa-testing $POD_NAME -- bash -c 'ps aux | grep -v grep | grep "python /app/app/http_server.py" && echo "✅ Server restarted with Vault integration!" || echo "❌ Server failed to start"'

echo ""
echo "📋 To check logs:"
echo "kubectl exec -n tinaa-testing $POD_NAME -- cat /tmp/restart.log"
echo ""
echo "🧪 To test Anthropic:"
echo "kubectl port-forward -n tinaa-testing service/tinaa-tinaa-playwright-msp 8765:8765 &"
echo "curl -X POST http://localhost:8765/test/exploratory -H 'Content-Type: application/json' -d '{\"action\":\"exploratory\",\"parameters\":{\"url\":\"https://example.com\",\"prompt\":\"Test Anthropic integration\"}}'"