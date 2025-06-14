# TINAA Troubleshooting Guide
## Comprehensive Problem Resolution

*Quick solutions to common issues and advanced debugging techniques for TINAA.*

---

## Quick Diagnostics

### Health Check Commands
```bash
# Basic health check
curl http://localhost:8765/health

# Expected response
{"status":"healthy","timestamp":"2024-01-01T00:00:00Z"}

# Extended diagnostics
curl http://localhost:8765/test/connectivity
```

## Common Status Indicators

| Status | Meaning | Action Required |
|--------|---------|-----------------|
| `{"status":"healthy"}` | ✅ All systems operational | None |
| `Connection refused` | ❌ TINAA not running | Start TINAA service |
| `{"status":"degraded"}` | ⚠️ Partial functionality | Check logs |
| `502 Bad Gateway` | ❌ Proxy/container issue | Restart services |

---

## Installation & Setup Issues

### Docker Issues

#### Problem: Container Won't Start
```bash
# Check container status
docker ps -a | grep tinaa

# View container logs
docker logs tinaa-container

# Common solutions
docker system prune  # Clean up docker
docker-compose down && docker-compose up -d  # Restart
```

**Common Causes:**
- Port 8765 already in use
- Insufficient memory
- Missing environment variables
- Corrupted docker image

**Solutions:**
```bash
# Check port usage
netstat -tlnp | grep 8765
# or
lsof -i :8765

# Kill process using port
sudo kill -9 $(lsof -t -i:8765)

# Check memory
docker stats

# Rebuild image
docker-compose build --no-cache
```

## Problem: Browser Installation Failed
```bash
# Check browser installation
docker exec -it tinaa-container playwright install --dry-run

# Fix: Reinstall browsers
docker exec -it tinaa-container playwright install chromium
```

## Local Python Installation Issues

#### Problem: Import Errors
```python
# Common error
ModuleNotFoundError: No module named 'playwright'

# Solution
pip install -r requirements.txt
playwright install chromium
```

## Problem: Permission Errors
```bash
# Linux/Mac permission fix
sudo chown -R $USER:$USER ~/.cache/ms-playwright

# Create logs directory
mkdir -p logs
chmod 755 logs
```

## Problem: Port Already in Use
```python
# Error: Address already in use
OSError: [Errno 98] Address already in use

# Solution: Use different port
python app/http_server.py --port 8766
```

---

## Runtime Errors

### Browser Connection Issues

#### Problem: Browser Failed to Launch
```json
{"error": "Browser failed to connect", "code": "BROWSER_ERROR"}
```

**Debugging Steps:**
```bash
# 1. Check system resources
free -h
df -h

# 2. Test browser manually
docker exec -it tinaa-container python -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    print('Browser launched successfully')
    browser.close()
"

# 3. Check Docker memory limits
docker inspect tinaa-container | grep -i memory

# 4. Increase memory allocation
docker run -m 4g tinaa-playwright-msp
```

**Common Solutions:**
```bash
# Increase shared memory for Docker
docker run --shm-size=2g tinaa-playwright-msp

# Add browser flags for containers
--no-sandbox --disable-dev-shm-usage
```

## Problem: Timeout Errors
```json
{"error": "Timeout 30000ms exceeded", "code": "TIMEOUT_ERROR"}
```

**Solutions:**
```bash
# Increase timeout globally
curl -X POST http://localhost:8765/configure \
  -d '{"default_timeout": 60000}'

# Check network connectivity
ping google.com
curl -I https://example.com

# Use faster DNS
echo "nameserver 8.8.8.8" >> /etc/resolv.conf
```

## Selector Issues

#### Problem: Element Not Found
```json
{"error": "Element not found: [data-testid='submit']", "code": "SELECTOR_ERROR"}
```

**Debugging Process:**
```bash
# 1. Debug specific selector
curl -X POST http://localhost:8765/debug/selectors \
  -d '{"selector": "[data-testid=submit]", "url": "https://example.com"}'

# 2. Get page analysis
curl -X POST http://localhost:8765/analyze_page \
  -d '{"url": "https://example.com"}'

# 3. Generate alternative selectors
curl -X POST http://localhost:8765/suggest_selectors \
  -d '{"text": "Submit", "url": "https://example.com"}'
```

**Manual Debugging:**
```javascript
// Browser console debugging
// 1. Check if element exists
document.querySelector('[data-testid="submit"]')

// 2. Find similar elements
document.querySelectorAll('[data-testid*="submit"]')

// 3. Check for dynamic IDs
document.querySelector('button[type="submit"]')

// 4. Use text content
document.querySelector('button:contains("Submit")')
```

## Performance Issues

#### Problem: Slow Test Execution
```bash
# Profile test execution
curl -X POST http://localhost:8765/test/exploratory \
  -d '{"action": "exploratory", "parameters": {"url": "URL", "profile": true}}'

# Check resource usage
docker stats tinaa-container

# Monitor network
curl -w "@curl-format.txt" -o /dev/null -s "URL"
```

**Optimization Strategies:**
```bash
# Enable performance mode
curl -X POST http://localhost:8765/configure \
  -d '{
    "performance_mode": true,
    "max_concurrent_tests": 1,
    "disable_images": true,
    "disable_fonts": true
  }'

# Use connection pooling
curl -X POST http://localhost:8765/configure \
  -d '{"connection_pooling": true, "pool_size": 5}'
```

---

## API & Integration Issues

### HTTP API Problems

#### Problem: 422 Validation Error
```json
{"detail": [{"loc": ["body", "url"], "msg": "field required"}]}
```

**Common Validation Issues:**
```bash
# Missing required fields
curl -X POST http://localhost:8765/test/exploratory \
  -H "Content-Type: application/json" \
  -d '{"action": "exploratory"}'  # Missing parameters

# Correct format
curl -X POST http://localhost:8765/test/exploratory \
  -H "Content-Type: application/json" \
  -d '{"action": "exploratory", "parameters": {"url": "https://example.com"}}'

# Invalid URL format
curl -X POST http://localhost:8765/navigate \
  -d '{"action": "navigate", "parameters": {"url": "not-a-url"}}'
```

## Problem: 429 Rate Limited
```json
{"detail": "Rate limit exceeded. Try again in 45.2 seconds"}
```

**Solutions:**
```bash
# Check current rate limits
curl http://localhost:8765/api/rate-limits

# Increase rate limits (if you control the server)
curl -X POST http://localhost:8765/configure \
  -d '{"rate_limit": {"requests_per_minute": 200}}'

# Use API key for higher limits
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8765/test/exploratory
```

## WebSocket Issues

#### Problem: WebSocket Connection Failed
```javascript
// Error: WebSocket connection to 'ws://localhost:8765/ws/client-123' failed
```

**Debugging Steps:**
```javascript
// 1. Test WebSocket endpoint
const ws = new WebSocket('ws://localhost:8765/ws/test-client');

ws.onopen = () => console.log('Connected');
ws.onerror = (error) => console.error('WebSocket error:', error);
ws.onclose = (event) => console.log('Closed:', event.code, event.reason);

// 2. Check network connectivity
fetch('http://localhost:8765/health')
  .then(response => response.json())
  .then(data => console.log('HTTP OK:', data))
  .catch(error => console.error('HTTP Error:', error));
```

**Common Solutions:**
```bash
# Check WebSocket support in load balancer
# NGINX configuration:
location /ws/ {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}

# Test direct connection (bypass proxy)
curl --include \
     --no-buffer \
     --header "Connection: Upgrade" \
     --header "Upgrade: websocket" \
     --header "Sec-WebSocket-Key: SGVsbG8sIHdvcmxkIQ==" \
     --header "Sec-WebSocket-Version: 13" \
     http://localhost:8765/ws/test
```

---

## Test Execution Problems

### Test Generation Issues

#### Problem: No Tests Generated
```json
{"success": true, "result": {"test_scenarios": []}}
```

**Debugging Steps:**
```bash
# 1. Check if page loads
curl -X POST http://localhost:8765/navigate \
  -d '{"action": "navigate", "parameters": {"url": "YOUR_URL"}}'

# 2. Verify page content
curl -X POST http://localhost:8765/analyze_page \
  -d '{"url": "YOUR_URL"}'

# 3. Check for JavaScript-heavy pages
curl -X POST http://localhost:8765/test/exploratory \
  -d '{
    "parameters": {
      "url": "YOUR_URL",
      "wait_for_javascript": true,
      "timeout": 60000
    }
  }'
```

**Common Causes & Solutions:**
```bash
# SPA (Single Page Application) issues
curl -X POST http://localhost:8765/test/exploratory \
  -d '{
    "parameters": {
      "url": "YOUR_URL",
      "wait_until": "networkidle",
      "focus_area": "spa"
    }
  }'

# Authentication required
curl -X POST http://localhost:8765/test/exploratory \
  -d '{
    "parameters": {
      "url": "YOUR_URL",
      "auth": {
        "username": "testuser",
        "password": "testpass"
      }
    }
  }'

# CAPTCHA or bot detection
curl -X POST http://localhost:8765/configure \
  -d '{
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "stealth_mode": true
  }'
```

## Problem: Poor Quality Tests Generated
```bash
# Enable debug mode for better insights
curl -X POST http://localhost:8765/test/exploratory \
  -d '{
    "parameters": {
      "url": "YOUR_URL",
      "debug": true,
      "verbose": true,
      "focus_area": "specific_feature"
    }
  }'

# Request specific test types
curl -X POST http://localhost:8765/test/exploratory \
  -d '{
    "parameters": {
      "url": "YOUR_URL",
      "test_types": ["forms", "navigation", "accessibility"],
      "depth": "comprehensive"
    }
  }'
```

## Accessibility Testing Issues

#### Problem: Accessibility Test Fails
```json
{"error": "Accessibility test failed", "details": "Page not loaded"}
```

**Solutions:**
```bash
# 1. Ensure page is loaded first
curl -X POST http://localhost:8765/navigate \
  -d '{"action": "navigate", "parameters": {"url": "YOUR_URL"}}'

# 2. Run accessibility test
curl -X POST http://localhost:8765/test/accessibility \
  -d '{"action": "accessibility", "parameters": {"standard": "WCAG2.1-AA"}}'

# 3. Check for iframe content
curl -X POST http://localhost:8765/test/accessibility \
  -d '{
    "parameters": {
      "include_iframes": true,
      "wait_for_content": true
    }
  }'
```

---

## Environment-Specific Issues

### Docker Deployment

#### Problem: Container Memory Issues
```bash
# Check memory usage
docker stats tinaa-container

# Increase memory allocation
docker run -m 8g tinaa-playwright-msp

# Monitor memory over time
watch 'docker stats --no-stream tinaa-container'
```

## Problem: File Permissions in Container
```bash
# Fix permission issues
docker exec -it tinaa-container chown -R playwright:playwright /app
docker exec -it tinaa-container chmod -R 755 /app/logs

# Check user context
docker exec -it tinaa-container whoami
docker exec -it tinaa-container id
```

## Kubernetes Deployment

#### Problem: Pod Crashes
```bash
# Check pod status
kubectl get pods -n tinaa-production

# View pod logs
kubectl logs -f deployment/tinaa-deployment -n tinaa-production

# Describe pod for events
kubectl describe pod POD_NAME -n tinaa-production

# Check resource limits
kubectl top pods -n tinaa-production
```

## Problem: Service Discovery Issues
```bash
# Test service connectivity
kubectl exec -it POD_NAME -n tinaa-production -- curl http://tinaa-service/health

# Check service endpoints
kubectl get endpoints tinaa-service -n tinaa-production

# Verify DNS resolution
kubectl exec -it POD_NAME -n tinaa-production -- nslookup tinaa-service
```

## Cloud Provider Issues

#### AWS-Specific Issues
```bash
# ECS task failures
aws ecs describe-tasks --cluster tinaa-cluster --tasks TASK_ID

# ALB health checks
aws elbv2 describe-target-health --target-group-arn TARGET_GROUP_ARN

# CloudWatch logs
aws logs get-log-events --log-group-name /aws/ecs/tinaa
```

## Azure-Specific Issues
```bash
# Container instance status
az container show --resource-group rg-tinaa --name tinaa-container

# Application Gateway health
az network application-gateway show-backend-health --resource-group rg-tinaa --name ag-tinaa
```

---

## Performance Debugging

### Memory Analysis

#### Memory Leak Detection
```bash
# Monitor memory over time
watch 'curl -s http://localhost:8765/system/memory'

# Generate heap dump
curl -X POST http://localhost:8765/debug/heap-dump

# Profile memory usage
curl -X POST http://localhost:8765/test/exploratory \
  -d '{"parameters": {"url": "URL", "memory_profile": true}}'
```

## Browser Memory Issues
```python
# app/debug/memory_monitor.py
import psutil
import asyncio
from datetime import datetime

class MemoryMonitor:
    def __init__(self):
        self.process = psutil.Process()
        self.snapshots = []
    
    async def take_snapshot(self, label: str):
        """Take memory snapshot."""
        memory_info = self.process.memory_info()
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "label": label,
            "rss": memory_info.rss,
            "vms": memory_info.vms,
            "percent": self.process.memory_percent()
        }
        self.snapshots.append(snapshot)
        return snapshot
    
    def analyze_leaks(self):
        """Analyze potential memory leaks."""
        if len(self.snapshots) < 2:
            return None
        
        initial = self.snapshots[0]
        final = self.snapshots[-1]
        
        return {
            "memory_growth": final["rss"] - initial["rss"],
            "growth_percent": ((final["rss"] - initial["rss"]) / initial["rss"]) * 100,
            "snapshots": self.snapshots
        }

# Usage
monitor = MemoryMonitor()

@app.middleware("http")
async def memory_monitoring_middleware(request: Request, call_next):
    await monitor.take_snapshot(f"start_{request.url.path}")
    response = await call_next(request)
    await monitor.take_snapshot(f"end_{request.url.path}")
    return response
```

## CPU Performance

#### High CPU Usage
```bash
# Monitor CPU usage
top -p $(pgrep -f tinaa)

# Profile CPU usage
curl -X POST http://localhost:8765/debug/cpu-profile \
  -d '{"duration": 30}'

# Check for resource contention
iostat -x 1 5
```

## Network Performance

#### Slow Response Times
```bash
# Test network latency
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8765/health

# curl-format.txt content:
# time_namelookup:  %{time_namelookup}\n
# time_connect:     %{time_connect}\n
# time_appconnect:  %{time_appconnect}\n
# time_pretransfer: %{time_pretransfer}\n
# time_redirect:    %{time_redirect}\n
# time_starttransfer: %{time_starttransfer}\n
# time_total:       %{time_total}\n

# Monitor network connections
netstat -tuln | grep 8765
ss -tuln | grep 8765
```

---

## Logging & Debugging

### Enable Debug Logging

```bash
# Start with debug logging
LOG_LEVEL=DEBUG python app/http_server.py

# Docker debug mode
docker run -e LOG_LEVEL=DEBUG -e PLAYWRIGHT_DEBUG=1 tinaa-playwright-msp

# Enable request tracing
curl -X POST http://localhost:8765/configure \
  -d '{"debug": {"requests": true, "responses": true}}'
```

## Log Analysis

```bash
# Real-time log monitoring
tail -f logs/tinaa.log

# Search for errors
grep -i error logs/tinaa.log

# Filter by timestamp
grep "2024-01-01" logs/tinaa.log

# Analyze request patterns
awk '/POST/ {print $7}' logs/access.log | sort | uniq -c | sort -nr
```

## Advanced Debugging

#### Enable Trace Recording
```python
# app/debug/tracer.py
import asyncio
import json
from datetime import datetime
from typing import Dict, Any

class RequestTracer:
    def __init__(self):
        self.traces = {}
    
    async def start_trace(self, request_id: str, context: Dict[str, Any]):
        """Start tracing a request."""
        self.traces[request_id] = {
            "start_time": datetime.now(),
            "context": context,
            "events": []
        }
    
    async def add_event(self, request_id: str, event: str, data: Any = None):
        """Add event to trace."""
        if request_id in self.traces:
            self.traces[request_id]["events"].append({
                "timestamp": datetime.now(),
                "event": event,
                "data": data
            })
    
    async def end_trace(self, request_id: str) -> Dict:
        """End tracing and return results."""
        if request_id not in self.traces:
            return None
        
        trace = self.traces[request_id]
        trace["end_time"] = datetime.now()
        trace["duration"] = (trace["end_time"] - trace["start_time"]).total_seconds()
        
        return trace

# Usage in request handling
tracer = RequestTracer()

@app.post("/test/exploratory")
async def traced_exploratory_test(request: TestRequest):
    request_id = generate_request_id()
    
    await tracer.start_trace(request_id, {
        "url": request.parameters.get("url"),
        "focus_area": request.parameters.get("focus_area")
    })
    
    try:
        await tracer.add_event(request_id, "browser_launch")
        # ... test execution
        await tracer.add_event(request_id, "test_complete", {"success": True})
        
        result = await execute_test(request)
        return result
        
    except Exception as e:
        await tracer.add_event(request_id, "error", {"error": str(e)})
        raise
    finally:
        trace = await tracer.end_trace(request_id)
        logger.info("request_trace", trace=trace)
```

---

## Error Recovery

### Automatic Recovery Strategies

```python
# app/recovery/auto_recovery.py
import asyncio
import logging
from typing import Callable, Any

class AutoRecovery:
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.logger = logging.getLogger(__name__)
    
    async def with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with automatic retry."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                self.logger.warning(
                    f"Attempt {attempt + 1} failed: {e}",
                    exc_info=True
                )
                
                if attempt < self.max_retries:
                    # Exponential backoff
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    
                    # Attempt recovery
                    await self.attempt_recovery(e)
        
        # All retries exhausted
        raise last_exception
    
    async def attempt_recovery(self, error: Exception):
        """Attempt to recover from specific errors."""
        error_type = type(error).__name__
        
        if "Browser" in str(error):
            await self.recover_browser()
        elif "Network" in str(error):
            await self.recover_network()
        elif "Memory" in str(error):
            await self.recover_memory()
    
    async def recover_browser(self):
        """Recover browser instances."""
        self.logger.info("Attempting browser recovery")
        # Restart browser instances
        controller = await get_controller()
        await controller.restart_browser()
    
    async def recover_network(self):
        """Recover network connectivity."""
        self.logger.info("Attempting network recovery")
        # Clear connection pools, reset DNS cache, etc.
        pass
    
    async def recover_memory(self):
        """Recover from memory issues."""
        self.logger.info("Attempting memory recovery")
        # Force garbage collection, clear caches
        import gc
        gc.collect()

# Usage
recovery = AutoRecovery()

@app.post("/test/exploratory")
async def resilient_exploratory_test(request: TestRequest):
    return await recovery.with_retry(execute_exploratory_test, request)
```

## Health Check Recovery

```bash
# Automated health monitoring script
#!/bin/bash
# monitor_tinaa.sh

HEALTH_URL="http://localhost:8765/health"
LOG_FILE="/var/log/tinaa_monitor.log"
MAX_FAILURES=3
failure_count=0

while true; do
    if curl -f -s $HEALTH_URL > /dev/null; then
        echo "$(date): TINAA healthy" >> $LOG_FILE
        failure_count=0
    else
        failure_count=$((failure_count + 1))
        echo "$(date): TINAA unhealthy (attempt $failure_count)" >> $LOG_FILE
        
        if [ $failure_count -ge $MAX_FAILURES ]; then
            echo "$(date): Restarting TINAA service" >> $LOG_FILE
            docker-compose restart tinaa
            failure_count=0
        fi
    fi
    
    sleep 30
done
```

---

## Getting Help

### Diagnostic Information Collection

```bash
#!/bin/bash
# collect_diagnostics.sh

echo "TINAA Diagnostic Information"
echo "=============================="
echo "Date: $(date)"
echo "System: $(uname -a)"
echo ""

echo "Docker Information:"
docker --version
docker-compose --version
echo ""

echo "Container Status:"
docker ps -a | grep tinaa
echo ""

echo "Container Logs (last 50 lines):"
docker logs --tail 50 tinaa-container
echo ""

echo "System Resources:"
free -h
df -h
echo ""

echo "Network Connectivity:"
curl -I http://localhost:8765/health
echo ""

echo "Configuration:"
curl -s http://localhost:8765/system/config
echo ""
```

## Support Channels

1. **GitHub Issues**: [Report bugs](https://github.com/aj-geddes/tinaa-playwright-msp/issues)
2. **Documentation**: [Complete guides](https://github.com/aj-geddes/tinaa-playwright-msp/docs)
3. **Community**: [Discussions](https://github.com/aj-geddes/tinaa-playwright-msp/discussions)

### Creating Effective Bug Reports

```markdown
## Bug Report Template

**Environment:**
- TINAA Version: 
- Operating System: 
- Docker Version: 
- Browser: 

**Issue Description:**
Brief description of the problem

**Steps to Reproduce:**
1. Step one
2. Step two
3. Step three

**Expected Behavior:**
What should happen

**Actual Behavior:**
What actually happens

**Error Messages:**
```
Paste error messages here
```text

**Diagnostic Information:**
```
Paste output from collect_diagnostics.sh
```text

**Additional Context:**
Any other relevant information
```

---

*This troubleshooting guide covers the most common issues and their solutions. For additional help, consult the full documentation or reach out through our support channels.*