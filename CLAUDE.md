# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TINAA (Testing Intelligence Network Automation Assistant) is an AI-powered Playwright testing platform that integrates with Claude Desktop via MCP (Model Context Protocol) and provides HTTP/WebSocket APIs for browser automation and intelligent test generation.

## Essential Commands

### Development
```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run MCP server (for Claude Desktop integration)
python app/main.py

# Run HTTP server with hot reload
python app/http_server.py --reload

# Run Language Server Protocol server
python playwright_lsp/server.py --tcp --port 8766
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# Run a single test file
pytest tests/unit/test_specific.py

# Run a single test function
pytest tests/unit/test_file.py::test_function_name
```

### Building & Deployment
```bash
# Docker build and run
docker build -t tinaa-playwright-msp .
docker run -p 8765:8765 tinaa-playwright-msp

# Helm deployment to Kubernetes
helm install tinaa charts/tinaa-playwright-msp/
helm upgrade tinaa charts/tinaa-playwright-msp/

# Direct Kubernetes deployment (without Vault)
kubectl apply -f deployment-no-vault.yaml
```

### Documentation
```bash
# Build and serve documentation locally
mkdocs serve

# Build static documentation
mkdocs build

# Deploy to GitHub Pages
mkdocs gh-deploy
```

## Architecture & Key Components

### Core Service Architecture
- **MCP Server** (`app/main.py`): Provides tools for Claude Desktop integration via Model Context Protocol
- **HTTP Server** (`app/http_server.py`): FastAPI server with REST endpoints and WebSocket support for real-time streaming
- **AI Integration** (`app/ai_integration.py`): Handles OpenAI and Anthropic API calls for test generation
- **Workspace Manager** (`app/workspace_manager.py`): Manages project workspaces and file system operations

### MCP Tools Available
The MCP server exposes these tools for browser automation:
- `navigate_to_url`: Navigate browser to URL
- `click_element`: Click on page elements
- `fill_form_field`: Input text into forms
- `take_screenshot`: Capture page screenshots
- `get_page_content`: Extract page text/HTML
- `run_test_suite`: Execute test scenarios
- `generate_test_from_ai`: AI-powered test generation

### API Endpoints (HTTP Mode)
- `POST /navigate`: Navigate to URL
- `POST /click`: Click element
- `POST /fill`: Fill form fields
- `POST /screenshot`: Take screenshot
- `GET /content`: Get page content
- `POST /test/run`: Run test suite
- `WebSocket /ws`: Real-time test execution updates

### Testing Framework Integration
The system supports multiple testing strategies in `resources/`:
- Exploratory testing
- Accessibility (WCAG) testing
- Responsive design testing
- Security testing
- Custom test scenarios

### AI Provider Configuration
Configure AI providers via environment variables:
- `ANTHROPIC_API_KEY`: For Claude integration
- `OPENAI_API_KEY`: For GPT integration

The AI integration layer (`app/ai_integration.py`) abstracts provider differences and handles:
- Test generation from natural language
- Page analysis and element detection
- Test result interpretation

## Development Guidelines

### Adding New MCP Tools
1. Define tool in `app/tinaa_mcp_server.py` using the `@mcp.tool()` decorator
2. Implement business logic, handling errors gracefully
3. Add corresponding tests in `tests/unit/test_mcp_tools.py`
4. Update documentation in `docs/tools/`

### Adding HTTP Endpoints
1. Define endpoint in `app/http_server.py` using FastAPI decorators
2. Implement request/response models in the same file
3. Add WebSocket support if real-time updates needed
4. Add tests in `tests/integration/test_http_endpoints.py`

### Working with AI Providers
1. AI provider abstraction is in `app/ai_integration.py`
2. Add new providers by implementing the base provider interface
3. Prompts are managed in `resources/prompts/`
4. Test with `test_ai_provider.py` scripts

### Kubernetes/Helm Modifications
1. Helm chart is in `charts/tinaa-playwright-msp/`
2. Values can be overridden with custom `values.yaml`
3. Supports horizontal scaling via HPA
4. Persistent volumes for workspace data

## Important Notes

- The project supports three modes: MCP (Claude Desktop), HTTP (REST API), and LSP (IDE integration)
- Playwright browsers are automatically installed in Docker containers
- Workspace data is mounted at `/mnt/workspace` in production
- Logs are written to `logs/` directory with rotation
- The system includes comprehensive error handling and retry logic for browser operations
- AI-generated tests are validated before execution to prevent harmful operations