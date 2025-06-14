# TINAA Testing Guide

## Overview

TINAA provides comprehensive browser testing capabilities through multiple specialized test types. This guide covers how to use each testing mode effectively.

## Test Types

### 1. Exploratory Testing

Exploratory testing uses AI-driven heuristics to automatically explore and test web applications.

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
    Start[Start URL] -.-> Analyze[Analyze Page]
    Analyze -.-> Elements[Find Interactive Elements]
    
    Elements -.-> Forms[Form Fields]
    Elements -.-> Links[Navigation Links]
    Elements -.-> Buttons[Buttons/Actions]
    
    Forms -.-> FillForm[Fill & Submit]
    Links -.-> Navigate[Follow Link]
    Buttons -.-> Click[Trigger Action]
    
    FillForm -.-> Check[Check Results]
    Navigate -.-> Check
    Click -.-> Check
    
    Check -.-> Errors{Errors Found?}
    Errors -.->|Yes| Report[Report Finding]
    Errors -.->|No| NextPage{More Pages?}
    
    Report -.-> NextPage
    NextPage -.->|Yes| Analyze
    NextPage -.->|No| Summary[Generate Summary]
```

**Configuration** (from `resources/exploratory_heuristics.json`):
- Navigation patterns
- Form interaction strategies
- Error detection rules
- Element prioritization

**Example Usage:**
```python
# Via MCP
result = await run_exploratory_test(
    url="https://example.com",
    max_depth=3,
    max_pages=10,
    include_forms=True
)

# Via HTTP API
response = requests.post(
    "http://localhost:8765/test/exploratory",
    json={
        "url": "https://example.com",
        "max_depth": 3,
        "include_forms": True
    }
)
```

## 2. Accessibility Testing

Tests websites against WCAG (Web Content Accessibility Guidelines) standards.

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
    Page[Load Page] -.-> Rules[Load WCAG Rules]
    
    Rules -.-> Perceivable[Perceivable]
    Rules -.-> Operable[Operable]
    Rules -.-> Understandable[Understandable]
    Rules -.-> Robust[Robust]
    
    Perceivable -.-> Images[Image Alt Text]
    Perceivable -.-> Color[Color Contrast]
    Perceivable -.-> Media[Media Alternatives]
    
    Operable -.-> Keyboard[Keyboard Access]
    Operable -.-> Focus[Focus Order]
    Operable -.-> Time[Time Limits]
    
    Understandable -.-> Labels[Form Labels]
    Understandable -.-> Errors[Error Messages]
    Understandable -.-> Language[Page Language]
    
    Robust -.-> Markup[Valid HTML]
    Robust -.-> ARIA[ARIA Usage]
    
    subgraph Checks["For Each Check"]
        Test[Run Test] -.-> Pass{Pass?}
        Pass -.->|No| Violation[Record Violation]
        Pass -.->|Yes| NextCheck[Next Check]
    end
    
    Images -.-> Checks
    Color -.-> Checks
    Keyboard -.-> Checks
    Labels -.-> Checks
    
    Violation -.-> Report[Generate Report]
    NextCheck -.-> Report
```

**WCAG Standards Supported:**
- WCAG 2.1 Level A
- WCAG 2.1 Level AA
- WCAG 2.1 Level AAA

**Checked Elements** (from `resources/accessibility_rules.json`):
- Images without alt text
- Form inputs without labels
- Insufficient color contrast
- Missing ARIA attributes
- Keyboard navigation issues
- Screen reader compatibility

### 3. Responsive Design Testing

Tests how websites adapt to different screen sizes and devices.

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
    URL[Target URL] -.-> Viewports[Define Viewports]
    
    Viewports -.-> Mobile[Mobile<br/>360x640]
    Viewports -.-> Tablet[Tablet<br/>768x1024]
    Viewports -.-> Desktop[Desktop<br/>1920x1080]
    
    Mobile -.-> Test1[Test Layout]
    Tablet -.-> Test2[Test Layout]
    Desktop -.-> Test3[Test Layout]
    
    Test1 -.-> Check1[Check Elements]
    Test2 -.-> Check2[Check Elements]
    Test3 -.-> Check3[Check Elements]
    
    Check1 -.-> Issues{Layout Issues?}
    Check2 -.-> Issues
    Check3 -.-> Issues
    
    Issues -.->|Yes| Document[Document Issue]
    Issues -.->|No| Next[Next Viewport]
    
    Document -.-> Screenshot[Take Screenshot]
    Screenshot -.-> Compare[Compare Layouts]
    Compare -.-> Report[Generate Report]
```

**Default Viewports Tested:**
- Mobile: 360x640, 375x667, 414x896
- Tablet: 768x1024, 834x1194
- Desktop: 1366x768, 1920x1080

**Checks Performed:**
- Text readability
- Element overflow
- Navigation usability
- Image scaling
- Touch target sizes

### 4. Security Testing

Performs basic, non-invasive security checks.

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
    Start[Start Security Test] -.-> Headers[Check Headers]
    Start -.-> Forms[Analyze Forms]
    Start -.-> Cookies[Inspect Cookies]
    Start -.-> Resources[Check Resources]
    
    Headers -.-> CSP[Content Security Policy]
    Headers -.-> XFO[X-Frame-Options]
    Headers -.-> HSTS[HSTS Header]
    
    Forms -.-> HTTPS[HTTPS Usage]
    Forms -.-> Autocomplete[Autocomplete Settings]
    Forms -.-> Validation[Input Validation]
    
    Cookies -.-> Secure[Secure Flag]
    Cookies -.-> HttpOnly[HttpOnly Flag]
    Cookies -.-> SameSite[SameSite Attribute]
    
    Resources -.-> Mixed[Mixed Content]
    Resources -.-> External[External Resources]
    
    CSP -.-> Findings[Security Findings]
    HTTPS -.-> Findings
    Secure -.-> Findings
    Mixed -.-> Findings
    
    Findings -.-> Severity{Severity Level}
    Severity -.-> High[High Risk]
    Severity -.-> Medium[Medium Risk]
    Severity -.-> Low[Low Risk]
    
    High -.-> Report[Security Report]
    Medium -.-> Report
    Low -.-> Report
```

**Security Checks** (from `resources/security_test_patterns.json`):
- HTTPS enforcement
- Security headers presence
- Cookie security flags
- Mixed content warnings
- Form security attributes
- Client-side validation
- Exposed sensitive data

### 5. Form Testing

Specialized testing for web forms and input validation.

**Form Test Strategies** (from `resources/form_test_strategies.json`):
- Field type detection
- Validation rule inference
- Boundary value testing
- Error message verification
- Submission flow testing

## Test Execution Flow

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
    participant User
    participant TINAA
    participant Browser
    participant Page
    participant Tracker as Progress Tracker
    
    User->>TINAA: Start Test
    TINAA->>Browser: Initialize Browser
    Browser-->>TINAA: Ready
    
    TINAA->>Tracker: Create Progress Tracker
    TINAA->>Page: Navigate to URL
    Page-->>TINAA: Page Loaded
    
    loop For Each Test Step
        TINAA->>Page: Execute Test Action
        Page-->>TINAA: Action Result
        TINAA->>Tracker: Update Progress
        Tracker-->>User: Progress Update
        
        alt Error Detected
            TINAA->>TINAA: Log Finding
            TINAA->>Page: Take Screenshot
        end
    end
    
    TINAA->>TINAA: Generate Report
    TINAA->>Browser: Cleanup
    TINAA-->>User: Final Report
```

## Progress Tracking

All tests provide real-time progress updates through the `ProgressTracker` system:

```python
# Progress update structure
{
    "category": "exploratory_test",
    "phase": "navigation",
    "message": "Analyzing page: /products",
    "data": {
        "current_page": 3,
        "total_pages": 10,
        "findings_count": 2
    },
    "timestamp": "2024-01-01T00:00:00Z"
}
```

## Test Reports

All tests generate comprehensive reports containing:

1. **Summary Section**
   - Test duration
   - Pages/elements tested
   - Total findings
   - Overall status

2. **Findings Section**
   - Severity levels (high/medium/low/info)
   - Detailed descriptions
   - Affected elements
   - Recommendations

3. **Screenshots Section**
   - Visual evidence
   - Annotated problem areas
   - Before/after comparisons

4. **Technical Details**
   - Browser information
   - Test configuration
   - Resource timings

## Best Practices

### 1. Test Preparation
- Ensure target site is accessible
- Use test/staging environments
- Have test credentials ready
- Clear browser cache/cookies

### 2. Configuration
- Start with default settings
- Adjust depth/pages based on site size
- Enable specific checks as needed
- Use appropriate WCAG level

### 3. Interpreting Results
- Focus on high-severity findings first
- Verify findings manually
- Consider false positives
- Use screenshots for context

### 4. Performance
- Limit concurrent tests
- Use reasonable depth limits
- Monitor resource usage
- Cache test results

## Advanced Usage

### Custom Test Patterns

You can extend test capabilities by modifying resource files:

1. **Exploratory Heuristics** (`resources/exploratory_heuristics.json`)
   - Add custom element selectors
   - Define new interaction patterns
   - Specify error indicators

2. **Accessibility Rules** (`resources/accessibility_rules.json`)
   - Add custom WCAG checks
   - Modify severity levels
   - Define element exceptions

3. **Security Patterns** (`resources/security_test_patterns.json`)
   - Add vulnerability patterns
   - Define security indicators
   - Specify header requirements

### Playbook Execution

Create reusable test sequences:

```json
{
  "name": "E-commerce Checkout Flow",
  "steps": [
    {
      "action": "navigate",
      "url": "https://shop.example.com"
    },
    {
      "action": "click",
      "selector": ".add-to-cart"
    },
    {
      "action": "navigate",
      "url": "https://shop.example.com/cart"
    },
    {
      "action": "fill",
      "selector": "#email",
      "value": "test@example.com"
    },
    {
      "action": "click",
      "selector": ".checkout-button"
    }
  ]
}
```

### Integration with CI/CD

```yaml
# Example GitHub Actions workflow
name: TINAA Tests
on: [push]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Run TINAA Tests
        run: |
          docker run --rm \
            -v $PWD:/workspace \
            tinaa-playwright-msp:latest \
            python -c "
            import asyncio
            from app.main import run_accessibility_test
            
            async def test():
                result = await run_accessibility_test(
                    'https://staging.example.com',
                    'WCAG2.1-AA'
                )
                print(result)
            
            asyncio.run(test())
            "
```

## Troubleshooting

### Common Issues

1. **Browser Launch Failures**
   - Check Docker permissions
   - Verify Playwright installation
   - Ensure sufficient memory

2. **Timeout Errors**
   - Increase timeout values
   - Check network connectivity
   - Verify site responsiveness

3. **False Positives**
   - Review detection rules
   - Check element selectors
   - Validate against manual testing

4. **Performance Issues**
   - Reduce test depth
   - Limit concurrent operations
   - Monitor resource usage

### Debug Mode

Enable detailed logging:
```python
# In docker-compose.yml
environment:
  - LOG_LEVEL=DEBUG
```

Check logs:
```bash
docker logs tinaa-playwright-msp
tail -f logs/app_main.log
```