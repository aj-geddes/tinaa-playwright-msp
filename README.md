# TINAA - Test Intelligence Network Automation Assistant

This is a Model Context Protocol (MCP) server for Playwright automation with integrated Language Server Protocol (LSP) for intelligent playbook creation assistance.

## Overview

TINAA provides comprehensive browser automation and testing capabilities through the MCP protocol, with support for both stdio communication and HTTP/WebSocket APIs for real-time progress tracking and IDE integration.

## Features

### Core Capabilities
- **Full Playwright Automation**: Complete browser control and interaction
- **Multi-Mode Operation**: 
  - MCP mode (stdio) for Claude integration
  - HTTP mode with WebSocket support for IDE integration
- **Real-Time Progress Tracking**: Live updates during test execution
- **Visual Playbook Builder**: IDE integration with drag-and-drop interface

### Testing Capabilities
- **Exploratory Testing**: Intelligent test generation with heuristics
- **Accessibility Testing**: WCAG 2.1 compliance validation
- **Responsive Design Testing**: Multi-viewport layout verification
- **Security Testing**: Basic vulnerability scanning
- **Form Analysis**: Automatic form field detection and filling

### Developer Features
- **Language Server Protocol**: Code assistance for Playwright scripts
- **Streaming Responses**: Progress updates for long-running operations
- **RESTful API**: Complete HTTP interface for all testing functions
- **WebSocket Support**: Bidirectional real-time communication

## Installation

### Using Docker (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/aj-geddes/tinaa-playwright-msp.git
   cd tinaa-playwright-msp
   ```

2. Build and run in MCP mode (for Claude):
   ```bash
   docker-compose up -d
   ```

3. Or run in HTTP mode (for IDE integration):
   ```bash
   docker-compose -f docker-compose.http.yml up -d
   ```

### Manual Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   python -m playwright install chromium
   ```

2. Run the server:
   ```bash
   # MCP mode
   python minimalist_mcp.py
   
   # HTTP mode
   python app/http_server.py
   ```

## Usage

### In Claude (MCP Mode)

Once the MCP server is running, you can use it in Claude with prompts like:

```
Can you test the accessibility of https://example.com?
```

```
Please run an exploratory test on the login form at https://example.com/login
```

```
Check the responsive design of https://example.com across different viewports
```

### IDE Integration (HTTP Mode)

1. Start the server in HTTP mode
2. Open `examples/ide_integration.html` in a web browser
3. Use the visual interface to build and execute test playbooks

### API Examples

#### Navigate to URL
```bash
curl -X POST http://localhost:8765/navigate \
  -H "Content-Type: application/json" \
  -d '{"action": "navigate", "parameters": {"url": "https://example.com"}}'
```

#### Run Exploratory Test
```bash
curl -X POST http://localhost:8765/test/exploratory \
  -H "Content-Type: application/json" \
  -d '{"action": "test_exploratory", "parameters": {}, "client_id": "test-client"}'
```

#### WebSocket Connection
```javascript
const ws = new WebSocket('ws://localhost:8765/ws/my-client-id');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Progress:', data);
};
```

## Configuration

### Environment Variables

- `TINAA_MODE`: Set to "http" for HTTP mode, defaults to MCP mode
- `PYTHONPATH`: Should include `/app`
- `PLAYWRIGHT_BROWSERS_PATH`: Browser installation path

### Docker Compose

Two compose files are provided:
- `docker-compose.yml`: Standard MCP mode
- `docker-compose.http.yml`: HTTP mode with health checks

## Architecture

```
tinaa-playwright-msp/
├── app/                    # Main application code
│   ├── main.py            # MCP server entry point
│   ├── http_server.py     # HTTP/WebSocket server
│   └── progress_tracker.py # Progress tracking system
├── playwright_controller/  # Browser automation logic
├── resources/             # Testing strategies and patterns
├── examples/              # Integration examples
└── docker-compose.yml     # Container configuration
```

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

Built with FastMCP, Playwright, and FastAPI.