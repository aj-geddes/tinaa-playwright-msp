# TINAA HTTP Mode - Streamable API with Progress Tracking

TINAA now supports HTTP mode with WebSocket connections for real-time progress updates and IDE integration.

## Features

- **HTTP REST API**: Full REST API for all TINAA testing capabilities
- **WebSocket Support**: Real-time progress updates and bidirectional communication
- **Streaming Responses**: Long-running tests stream progress updates
- **Playbook Builder**: Create and execute test playbooks programmatically
- **IDE Integration**: Example HTML interface demonstrating IDE integration

## Running TINAA in HTTP Mode

### Using Docker Compose

```bash
# Build the image
docker-compose -f docker-compose.http.yml build

# Run in HTTP mode
docker-compose -f docker-compose.http.yml up

# Or run in detached mode
docker-compose -f docker-compose.http.yml up -d
```

## Using Docker directly

```bash
# Build the image
docker build -t tinaa-playwright-msp:latest .

# Run in HTTP mode
docker run -d \
  --name tinaa-http \
  -p 8765:8765 \
  -e TINAA_MODE=http \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd):/mnt/workspace \
  tinaa-playwright-msp:latest
```

## API Endpoints

### Health Check
```text
GET http://localhost:8765/health
```

### Test Connectivity
```javascript
POST http://localhost:8765/test/connectivity
{
  "action": "test_connectivity",
  "parameters": {},
  "client_id": "optional-client-id"
}
```

### Navigate to URL
```text
POST http://localhost:8765/navigate
{
  "action": "navigate",
  "parameters": {
    "url": "https://example.com"
  },
  "client_id": "optional-client-id"
}
```

### Take Screenshot
```text
POST http://localhost:8765/screenshot
{
  "action": "screenshot",
  "parameters": {
    "type": "page",
    "full_page": true
  },
  "client_id": "optional-client-id"
}
```

### Run Tests (Streaming)

All test endpoints support streaming responses with progress updates:

- `/test/exploratory` - Run exploratory test
- `/test/accessibility` - Run accessibility test
- `/test/responsive` - Run responsive test
- `/test/security` - Run security test

### Execute Playbook
```javascript
POST http://localhost:8765/playbook/execute
{
  "name": "My Test Playbook",
  "steps": [
    {
      "id": "step-1",
      "action": "navigate",
      "parameters": {"url": "https://example.com"}
    },
    {
      "id": "step-2",
      "action": "test_exploratory",
      "parameters": {}
    }
  ],
  "client_id": "my-client-id"
}
```

## WebSocket Connection

Connect to WebSocket for real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:8765/ws/my-client-id');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'progress') {
    console.log('Progress:', data.data);
  }
};

// Send commands
ws.send(JSON.stringify({
  type: 'execute',
  action: 'navigate',
  parameters: { url: 'https://example.com' }
}));
```

## Progress Updates

Progress updates include:

```json
{
  "type": "progress",
  "data": {
    "message": "Testing element-5",
    "level": "info",
    "timestamp": "2023-11-20T10:30:45.123Z",
    "progress": 65.5,
    "metadata": {
      "phase": "interaction_testing",
      "element_index": 5,
      "total_elements": 10
    }
  }
}
```

## IDE Integration Example

Open `examples/ide_integration.html` in a browser to see a working example of:

- Visual playbook builder
- Real-time progress tracking
- WebSocket communication
- Interactive test execution

## Switching Between Modes

The same Docker image supports both MCP and HTTP modes:

```bash
# MCP Mode (default)
docker run -e TINAA_MODE=mcp ...

# HTTP Mode
docker run -e TINAA_MODE=http ...
```

## Development

The HTTP server is built with:
- FastAPI for REST endpoints
- WebSocket support for real-time communication
- Async/await for concurrent operations
- Progress tracking system for detailed updates

Key files:
- `app/http_server.py` - Main HTTP server
- `app/progress_tracker.py` - Progress tracking system
- `app/enhanced_mcp_handler.py` - Enhanced handlers with progress support