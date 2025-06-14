# TINAA Architecture Documentation

## System Components

```mermaid
%%{init: {
  'theme': 'dark',
  'themeVariables': {
    'fontFamily': 'monospace',
    'primaryBorderColor': '#6BB4DD',
    'primaryColor': '#2D3A4D',
    'primaryTextColor': '#fff',
    'lineColor': '#6BB4DD'
  },
  'themeCSS': '.node rect, .node circle, .node polygon, .node path { stroke-width: 2px; stroke-dasharray: 3,3; } .nodeLabel { font-family: monospace; } .edgeLabel { font-family: monospace; } #flowchart line, .path, #statediagram-barbEnd, path.messageLineC { stroke-width: 1.5px; stroke-dasharray: 3,3; }'
}}%%
flowchart TD
    subgraph External["External Interfaces"]
        Claude[Claude Desktop<br/>MCP Client]
        Browser[Web Browser<br/>HTTP Client]
        Editor[Code Editor<br/>LSP Client]
    end
    
    subgraph Interface["Interface Layer"]
        MCP[MCP Server<br/>FastMCP Framework]
        HTTP[HTTP Server<br/>FastAPI + WebSocket]
        LSP[LSP Server<br/>pygls Framework]
    end
    
    subgraph Logic["Business Logic Layer"]
        Handler[MCP Handler<br/>mcp_handler.py]
        Routes[API Routes<br/>http_server.py]
        Handlers[LSP Handlers<br/>handlers/]
    end
    
    subgraph Core["Core Services"]
        PC[Playwright Controller<br/>controller.py]
        PT[Progress Tracker<br/>progress_tracker.py]
        RL[Resource Loader<br/>resource_loader.py]
        Tools[Tool System<br/>tools/]
    end
    
    subgraph Resources["Resource Layer"]
        JSON[JSON Resources<br/>resources/]
        Prompts[Prompt Templates<br/>prompts/]
        Static[Static Assets<br/>static/]
    end
    
    subgraph Browser["Browser Engine"]
        PW[Playwright API]
        Chrome[Chromium Instance]
    end
    
    Claude -.->|stdio| MCP
    Browser -.->|HTTP/WS| HTTP
    Editor -.->|TCP/stdio| LSP
    
    MCP -.-> Handler
    HTTP -.-> Routes
    LSP -.-> Handlers
    
    Handler -.-> PC
    Routes -.-> PC
    Handlers -.-> PC
    
    PC -.-> PT
    PC -.-> RL
    PC -.-> Tools
    
    RL -.-> JSON
    Tools -.-> Prompts
    Routes -.-> Static
    
    PC -.-> PW
    PW -.-> Chrome
```

## Class Architecture

```mermaid
%%{init: {
  'theme': 'dark',
  'themeVariables': {
    'fontFamily': 'monospace',
    'primaryBorderColor': '#6BB4DD',
    'primaryColor': '#2D3A4D',
    'primaryTextColor': '#fff',
    'lineColor': '#6BB4DD'
  }
}}%%
classDiagram
    class PlaywrightController {
        -playwright: Playwright
        -browser: Browser
        -context: BrowserContext
        -page: Page
        -screenshots: List[Dict]
        -findings: Dict[str, List]
        +initialize(viewport_size, user_agent, locale) bool
        +navigate(url: str) Dict
        +screenshot(name: str) Dict
        +run_exploratory_test(url, max_depth) Dict
        +run_accessibility_test(url, standard) Dict
        +cleanup() None
    }
    
    class ProgressTracker {
        #progress_data: Dict
        #lock: asyncio.Lock
        +update_progress(category, phase, message, data)
        +get_progress() Dict
        +reset() None
    }
    
    class ExploratoryTestProgress {
        +update_navigation(url, depth)
        +add_interaction(element, action, result)
        +add_finding(type, severity, details)
        +get_summary() Dict
    }
    
    class AccessibilityTestProgress {
        +update_rule_check(rule, status, details)
        +add_violation(rule, severity, element, message)
        +get_wcag_summary() Dict
    }
    
    class ResourceLoader {
        -_instance: ResourceLoader
        -resources_dir: Path
        -_cache: Dict
        +load_resource(name: str) Dict
        +get_exploratory_heuristics() Dict
        +get_accessibility_rules() Dict
        +get_security_patterns() Dict
    }
    
    class ConnectionManager {
        -active_connections: Dict[str, WebSocket]
        +connect(client_id, websocket)
        +disconnect(client_id)
        +send_message(client_id, message)
        +broadcast(message)
    }
    
    class ProgressContext {
        -tracker: ProgressTracker
        -category: str
        +__aenter__()
        +__aexit__()
        +update(phase, message, data)
    }
    
    ProgressTracker <|-- ExploratoryTestProgress : extends
    ProgressTracker <|-- AccessibilityTestProgress : extends
    PlaywrightController *-- ProgressTracker : uses
    PlaywrightController *-- ResourceLoader : uses
    ProgressContext *-- ProgressTracker : wraps
```

## Request Flow Sequence

```mermaid
%%{init: {
  'theme': 'dark',
  'themeVariables': {
    'fontFamily': 'monospace',
    'primaryBorderColor': '#6BB4DD',
    'primaryColor': '#2D3A4D',
    'primaryTextColor': '#fff',
    'lineColor': '#6BB4DD',
    'activationBorderColor': '#6BB4DD'
  },
  'themeCSS': '.messageText, .loopText, .noteText { font-family: monospace; } .messageLine0, .messageLine1 { stroke-width: 1.5px; stroke-dasharray: 3,3; }'
}}%%
sequenceDiagram
    participant Client
    participant Server as MCP/HTTP Server
    participant Handler
    participant Controller as Playwright Controller
    participant Tracker as Progress Tracker
    participant Browser
    
    Client->>Server: Request (navigate/test)
    activate Server
    Server->>Handler: Process request
    activate Handler
    
    Handler->>Controller: Initialize if needed
    activate Controller
    Controller->>Browser: Launch browser
    activate Browser
    Browser-->>Controller: Browser ready
    
    Handler->>Tracker: Create progress tracker
    activate Tracker
    
    loop For each operation
        Handler->>Controller: Execute operation
        Controller->>Browser: Browser action
        Browser-->>Controller: Result
        Controller->>Tracker: Update progress
        Tracker-->>Client: Progress update (if streaming)
    end
    
    Controller-->>Handler: Final result
    deactivate Controller
    Handler-->>Server: Response
    deactivate Handler
    Server-->>Client: Final response
    deactivate Server
    
    deactivate Browser
    deactivate Tracker
```

## State Management

```mermaid
%%{init: {
  'theme': 'dark',
  'themeVariables': {
    'fontFamily': 'monospace',
    'primaryBorderColor': '#6BB4DD',
    'primaryColor': '#2D3A4D',
    'primaryTextColor': '#fff',
    'lineColor': '#6BB4DD'
  },
  'themeCSS': '.stateText { font-family: monospace; } .statePath { stroke-width: 1.5px; stroke-dasharray: 3,3; }'
}}%%
stateDiagram-v2
    [*] --> Uninitialized
    Uninitialized --> Initializing: initialize()
    Initializing --> Ready: success
    Initializing --> Error: failure
    
    Ready --> Navigating: navigate()
    Navigating --> PageLoaded: success
    Navigating --> Error: failure
    
    PageLoaded --> Testing: run_test()
    Testing --> TestComplete: success
    Testing --> Error: failure
    
    TestComplete --> Ready: reset
    Error --> Ready: retry
    
    Ready --> Cleanup: cleanup()
    PageLoaded --> Cleanup: cleanup()
    TestComplete --> Cleanup: cleanup()
    Cleanup --> [*]
    
    state Testing {
        [*] --> StartPhase
        StartPhase --> InProgress
        InProgress --> CompletePhase
        CompletePhase --> [*]
        
        InProgress --> Warning: non-critical issue
        Warning --> InProgress: continue
        InProgress --> TestError: critical issue
    }
```

## Data Flow

```mermaid
%%{init: {
  'theme': 'dark',
  'themeVariables': {
    'fontFamily': 'monospace',
    'primaryBorderColor': '#6BB4DD',
    'primaryColor': '#2D3A4D',
    'primaryTextColor': '#fff',
    'lineColor': '#6BB4DD'
  },
  'themeCSS': '.node rect, .node circle, .node polygon { stroke-width: 2px; stroke-dasharray: 3,3; }'
}}%%
flowchart LR
    subgraph Input["Input Sources"]
        User[User Request]
        Config[Configuration]
        Resources[Resource Files]
    end
    
    subgraph Processing["Processing Layer"]
        Validation[Request Validation]
        Controller[Controller Logic]
        Engine[Test Engine]
    end
    
    subgraph Storage["Data Storage"]
        Memory[In-Memory Cache]
        Screenshots[Screenshot Buffer]
        Findings[Findings Collection]
    end
    
    subgraph Output["Output Formats"]
        JSON[JSON Response]
        Stream[Streaming Updates]
        Report[Test Report]
    end
    
    User -.-> Validation
    Config -.-> Validation
    Resources -.-> Controller
    
    Validation -.-> Controller
    Controller -.-> Engine
    
    Engine -.-> Memory
    Engine -.-> Screenshots
    Engine -.-> Findings
    
    Memory -.-> JSON
    Screenshots -.-> Report
    Findings -.-> Report
    Memory -.-> Stream
```

## Resource Structure

```mermaid
%%{init: {
  'theme': 'dark',
  'themeVariables': {
    'fontFamily': 'monospace',
    'primaryBorderColor': '#6BB4DD',
    'primaryColor': '#2D3A4D',
    'primaryTextColor': '#fff',
    'lineColor': '#6BB4DD'
  },
  'themeCSS': '.node rect, .node circle, .node polygon { stroke-width: 2px; stroke-dasharray: 3,3; }'
}}%%
flowchart TD
    Root[resources/] -.-> Accessibility[accessibility_rules.json]
    Root -.-> Exploratory[exploratory_heuristics.json]
    Root -.-> Security[security_test_patterns.json]
    Root -.-> Forms[form_test_strategies.json]
    Root -.-> Responsive[responsive_test_config.json]
    Root -.-> Credentials[test_credentials.json]
    
    Accessibility -.-> WCAG[WCAG 2.1 Rules]
    Exploratory -.-> Heuristics[Test Heuristics]
    Security -.-> Patterns[Security Patterns]
    
    WCAG -.-> A[Level A]
    WCAG -.-> AA[Level AA]
    WCAG -.-> AAA[Level AAA]
    
    Heuristics -.-> Nav[Navigation]
    Heuristics -.-> Forms_H[Form Testing]
    Heuristics -.-> Int[Interactions]
```

## Deployment Architecture

```mermaid
%%{init: {
  'theme': 'dark',
  'themeVariables': {
    'fontFamily': 'monospace',
    'primaryBorderColor': '#6BB4DD',
    'primaryColor': '#2D3A4D',
    'primaryTextColor': '#fff',
    'lineColor': '#6BB4DD'
  },
  'themeCSS': '.node rect, .node circle, .node polygon { stroke-width: 2px; stroke-dasharray: 3,3; }'
}}%%
flowchart TD
    subgraph Host["Host System"]
        Docker[Docker Engine]
        Volumes[Volume Mounts]
    end
    
    subgraph Container["TINAA Container"]
        Base[Base Image<br/>playwright:v1.46.1-jammy]
        Python[Python 3.11]
        App[Application Code]
        Browsers[Chromium Browser]
    end
    
    subgraph Network["Network"]
        Port8765[Port 8765<br/>MCP/HTTP]
        Stdio[STDIO<br/>MCP Mode]
    end
    
    subgraph Storage["Persistent Storage"]
        Logs[logs/]
        Workspace[/mnt/workspace]
    end
    
    Docker -.-> Container
    Container -.-> Network
    Volumes -.-> Storage
    
    App -.-> Python
    Python -.-> Browsers
    Base -.-> Browsers
    
    App -.-> Port8765
    App -.-> Stdio
    
    App -.-> Logs
    App -.-> Workspace
```

## Error Handling Flow

```mermaid
%%{init: {
  'theme': 'dark',
  'themeVariables': {
    'fontFamily': 'monospace',
    'primaryBorderColor': '#6BB4DD',
    'primaryColor': '#2D3A4D',
    'primaryTextColor': '#fff',
    'lineColor': '#6BB4DD'
  },
  'themeCSS': '.node rect, .node circle, .node polygon { stroke-width: 2px; stroke-dasharray: 3,3; }'
}}%%
flowchart TD
    Operation[Operation] -.-> Try{Try Block}
    
    Try -.->|Success| Result[Return Result]
    Try -.->|Exception| Catch{Exception Type}
    
    Catch -.->|Playwright Error| BrowserError[Log Browser Error]
    Catch -.->|Timeout| TimeoutError[Handle Timeout]
    Catch -.->|Network| NetworkError[Retry Logic]
    Catch -.->|Other| GeneralError[General Handler]
    
    BrowserError -.-> Cleanup[Cleanup Resources]
    TimeoutError -.-> Cleanup
    NetworkError -.->|Retry| Operation
    NetworkError -.->|Max Retries| Cleanup
    GeneralError -.-> Cleanup
    
    Cleanup -.-> LogError[Log to File]
    LogError -.-> ReturnError[Return Error Response]
```

## Testing Strategy

```mermaid
%%{init: {
  'theme': 'dark',
  'themeVariables': {
    'fontFamily': 'monospace',
    'primaryBorderColor': '#6BB4DD',
    'primaryColor': '#2D3A4D',
    'primaryTextColor': '#fff',
    'lineColor': '#6BB4DD'
  },
  'themeCSS': '.node rect, .node circle, .node polygon { stroke-width: 2px; stroke-dasharray: 3,3; }'
}}%%
flowchart TD
    subgraph TestTypes["Test Categories"]
        Unit[Unit Tests<br/>tests/unit/]
        Integration[Integration Tests<br/>tests/integration/]
        E2E[E2E Tests<br/>tests/e2e/]
    end
    
    subgraph Coverage["Test Coverage"]
        MCP_T[MCP Protocol]
        HTTP_T[HTTP API]
        Controller_T[Controller Logic]
        Resources_T[Resource Loading]
    end
    
    subgraph Tools["Testing Tools"]
        Pytest[pytest]
        Coverage_Tool[pytest-cov]
        Playwright_Test[pytest-playwright]
    end
    
    Unit -.-> MCP_T
    Unit -.-> Controller_T
    Unit -.-> Resources_T
    
    Integration -.-> HTTP_T
    Integration -.-> Controller_T
    
    E2E -.-> MCP_T
    E2E -.-> HTTP_T
    
    TestTypes -.-> Tools
```

## Key Design Patterns

1. **Singleton Pattern**: ResourceLoader ensures single instance for resource management
2. **Factory Pattern**: Tool loading system dynamically loads testing tools
3. **Context Manager**: ProgressContext provides scoped progress tracking
4. **Observer Pattern**: WebSocket connections for real-time updates
5. **Strategy Pattern**: Different progress trackers for different test types
6. **Adapter Pattern**: MCP/HTTP/LSP servers adapt to common controller interface

## Performance Considerations

- **Async Operations**: All I/O operations use async/await for non-blocking execution
- **Resource Caching**: ResourceLoader caches JSON files to avoid repeated disk reads
- **Connection Pooling**: WebSocket connections managed in ConnectionManager
- **Lazy Initialization**: Browser only launched when needed
- **Streaming Responses**: Large test results streamed rather than buffered

## Security Architecture

- **Headless Execution**: Browser runs in headless mode for security
- **Input Validation**: All inputs validated using Pydantic models
- **Credential Management**: Test credentials stored separately in JSON
- **Non-Invasive Testing**: Security tests designed to be read-only
- **Isolated Execution**: Docker container provides isolation
- **No Persistent State**: Stateless design prevents data leakage between sessions