#!/bin/bash
# Verify TINAA pod secrets and Anthropic configuration

echo "🔍 TINAA Pod Secret Verification Script"
echo "======================================="

# Get TINAA pod name (adjust namespace if needed)
NAMESPACE="${NAMESPACE:-default}"
POD_NAME=$(kubectl get pods -n $NAMESPACE -l app=tinaa -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$POD_NAME" ]; then
    echo "❌ No TINAA pod found in namespace '$NAMESPACE'"
    echo "   Try: export NAMESPACE=your-namespace"
    exit 1
fi

echo "✅ Found TINAA pod: $POD_NAME"
echo ""

echo "📋 1. Checking pod environment variables..."
echo "----------------------------------------"
kubectl exec -n $NAMESPACE $POD_NAME -- env | grep -E "(ANTHROPIC|TINAA|AI_)" | sort

echo ""
echo "🔐 2. Checking mounted secrets..."
echo "--------------------------------"
kubectl exec -n $NAMESPACE $POD_NAME -- ls -la /var/run/secrets/ 2>/dev/null || echo "No secrets in /var/run/secrets/"
kubectl exec -n $NAMESPACE $POD_NAME -- ls -la /etc/secrets/ 2>/dev/null || echo "No secrets in /etc/secrets/"
kubectl exec -n $NAMESPACE $POD_NAME -- ls -la /secrets/ 2>/dev/null || echo "No secrets in /secrets/"

echo ""
echo "🔍 3. Checking for Anthropic secret specifically..."
echo "-------------------------------------------------"
# Check if the secret exists in Kubernetes
SECRET_EXISTS=$(kubectl get secret tinaa-anthropic-secret -n $NAMESPACE -o name 2>/dev/null)
if [ -n "$SECRET_EXISTS" ]; then
    echo "✅ Secret 'tinaa-anthropic-secret' exists in Kubernetes"
    
    # Check secret keys
    echo "   Keys in secret:"
    kubectl get secret tinaa-anthropic-secret -n $NAMESPACE -o jsonpath='{.data}' | jq -r 'keys[]' 2>/dev/null || \
    kubectl get secret tinaa-anthropic-secret -n $NAMESPACE -o jsonpath='{.data}' | grep -o '"[^"]*":' | sed 's/"://g' | sed 's/"//g'
else
    echo "❌ Secret 'tinaa-anthropic-secret' not found in namespace '$NAMESPACE'"
fi

echo ""
echo "📁 4. Checking pod mounts..."
echo "--------------------------"
kubectl describe pod -n $NAMESPACE $POD_NAME | grep -A5 "Mounts:" | grep -E "(secret|anthropic)"

echo ""
echo "🧪 5. Testing secret access inside pod..."
echo "---------------------------------------"
# Try to read the secret from common mount points
kubectl exec -n $NAMESPACE $POD_NAME -- bash -c '
for path in /var/run/secrets/tinaa-anthropic-secret /etc/secrets/tinaa-anthropic-secret /secrets/tinaa-anthropic-secret; do
    if [ -d "$path" ]; then
        echo "✅ Found secret directory: $path"
        ls -la "$path"
        if [ -f "$path/api-key" ]; then
            echo "   ✅ api-key file exists (length: $(wc -c < "$path/api-key") bytes)"
        fi
    fi
done
'

echo ""
echo "💡 6. Quick fixes if secret is not accessible:"
echo "--------------------------------------------"
echo "1. Create the secret if it doesn't exist:"
echo "   kubectl create secret generic tinaa-anthropic-secret \\"
echo "     --from-literal=api-key='your-anthropic-api-key' \\"
echo "     --from-literal=base-url='https://api.anthropic.com' \\"
echo "     --from-literal=default-model='claude-3-sonnet-20240229'"
echo ""
echo "2. Update deployment to mount the secret:"
echo "   kubectl edit deployment tinaa -n $NAMESPACE"
echo "   # Add under spec.template.spec.volumes:"
echo "   - name: anthropic-secret"
echo "     secret:"
echo "       secretName: tinaa-anthropic-secret"
echo "   # Add under spec.template.spec.containers[0].volumeMounts:"
echo "   - name: anthropic-secret"
echo "     mountPath: /var/run/secrets/tinaa-anthropic-secret"
echo "     readOnly: true"
echo ""
echo "3. Or set as environment variable:"
echo "   kubectl set env deployment/tinaa -n $NAMESPACE \\"
echo "     TINAA_ANTHROPIC_SECRET_API_KEY='your-api-key'"