# Tinaa Playwright MSP

This MCP server provides Playwright integration for automated testing and UI analysis through Claude, using fastmcp version 2.8.0.

## Features

- Full Playwright automation capabilities
- Browser-based testing and analysis
- Accessibility testing
- Responsive design testing
- Form analysis and testing

## Setup

1. Make sure Docker and Docker Compose are installed on your system.

2. Build and run the Docker container:
   ```
   docker-compose up -d
   ```

3. To check logs:
   ```
   docker-compose logs
   ```

4. To stop the container:
   ```
   docker-compose down
   ```

## Usage in Claude

Once the MCP server is running, you can use it in Claude by connecting to the MCP server.

Example prompts:

```
Can you use Playwright to test the accessibility of my website at https://example.com?
```

```
Can you use Playwright to analyze the login form at https://example.com/login?
```

```
Can you use Playwright to check the responsive design of my website at https://example.com?
```
