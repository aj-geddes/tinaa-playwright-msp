# TINAA Playwright MSP Helm Chart

This Helm chart deploys TINAA (Testing Intelligence Network Automation Assistant) on a Kubernetes cluster.

## Prerequisites

- Kubernetes 1.19+
- Helm 3.2.0+
- PV provisioner support in the underlying infrastructure (if using persistence)

## Installing the Chart

To install the chart with the release name `tinaa`:

```bash
# From the repository root
helm install tinaa ./charts/tinaa-playwright-msp

# Or with custom values
helm install tinaa ./charts/tinaa-playwright-msp -f my-values.yaml

# Install in a specific namespace
helm install tinaa ./charts/tinaa-playwright-msp -n tinaa-namespace --create-namespace
```

## Uninstalling the Chart

```bash
helm uninstall tinaa
```

## Configuration

The following table lists the configurable parameters of the TINAA chart and their default values.

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas | `1` |
| `image.repository` | Image repository | `ghcr.io/aj-geddes/tinaa-playwright-msp` |
| `image.tag` | Image tag | `latest` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `service.type` | Kubernetes service type | `ClusterIP` |
| `service.port` | Service port | `8765` |
| `ingress.enabled` | Enable ingress | `false` |
| `resources.limits.cpu` | CPU limit | `2` |
| `resources.limits.memory` | Memory limit | `4Gi` |
| `resources.requests.cpu` | CPU request | `500m` |
| `resources.requests.memory` | Memory request | `2Gi` |
| `tinaa.mode` | TINAA mode (http/mcp) | `http` |
| `tinaa.persistence.logs.enabled` | Enable logs persistence | `true` |
| `tinaa.persistence.logs.size` | Logs volume size | `5Gi` |
| `tinaa.persistence.workspace.enabled` | Enable workspace persistence | `true` |
| `tinaa.persistence.workspace.size` | Workspace volume size | `10Gi` |

### Example Values for Production

```yaml
# values-prod.yaml
replicaCount: 2

resources:
  limits:
    cpu: 4
    memory: 8Gi
  requests:
    cpu: 2
    memory: 4Gi

ingress:
  enabled: true
  className: nginx
  hosts:
    - host: tinaa.example.com
      paths:
        - path: /
          pathType: ImplementationSpecific
  tls:
    - secretName: tinaa-tls
      hosts:
        - tinaa.example.com

tinaa:
  persistence:
    logs:
      enabled: true
      storageClass: fast-ssd
      size: 20Gi
    workspace:
      enabled: true
      storageClass: fast-ssd
      size: 50Gi
```

## Security Considerations

TINAA requires `SYS_ADMIN` capability for browser automation. This is configured in the pod security context:

```yaml
securityContext:
  capabilities:
    add:
      - SYS_ADMIN
```

For enhanced security, consider:
1. Using NetworkPolicies to restrict traffic
2. Running in a dedicated namespace
3. Using RBAC to limit permissions
4. Enabling pod security policies if required

## Persistence

The chart supports persistent storage for:
- **Logs**: Application logs at `/app/logs`
- **Workspace**: Test files and artifacts at `/mnt/workspace`

To use existing PVCs:

```yaml
tinaa:
  persistence:
    logs:
      existingClaim: my-logs-pvc
    workspace:
      existingClaim: my-workspace-pvc
```

## Monitoring

To add Prometheus monitoring:

```yaml
podAnnotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8765"
  prometheus.io/path: "/metrics"
```

## Troubleshooting

### Pod not starting

Check pod events:
```bash
kubectl describe pod -l app.kubernetes.io/name=tinaa-playwright-msp
```

### Browser tests failing

Ensure the pod has sufficient resources:
```bash
kubectl top pod -l app.kubernetes.io/name=tinaa-playwright-msp
```

### Persistent volumes not mounting

Check PVC status:
```bash
kubectl get pvc -l app.kubernetes.io/name=tinaa-playwright-msp
```

## Support

For more information, visit: https://aj-geddes.github.io/tinaa-playwright-msp