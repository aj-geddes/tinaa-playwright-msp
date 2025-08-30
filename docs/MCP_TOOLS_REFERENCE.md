# TINAA MCP Tools Reference

Complete reference for all TINAA MCP tools compatible with FastMCP 2.8.0 framework. This document covers all available tools for collaborative test design, workspace management, and AI-powered testing assistance.

## Overview

TINAA provides comprehensive MCP (Model Context Protocol) integration allowing LLM-enabled IDEs to interact with TINAA's testing capabilities. All tools follow FastMCP 2.8.0 standards with detailed documentation, type hints, and examples.

## Tool Categories

### 🤝 Collaborative Test Design Tools
Tools for interactive test design sessions between TINAA and IDE LLMs.

### 🗂️ Workspace Management Tools  
Tools for managing testing projects, repositories, and workspace organization.

### 🔧 Browser Automation Tools
Core Playwright automation and testing capabilities.

### 🧠 AI Assistant Tools
AI-powered problem solving, code review, and optimization.

---

## 🤝 Collaborative Test Design Tools

### `start_collaborative_session`

Start an intelligent collaborative test design session between TINAA and your IDE.

**Purpose**: Initiates an interactive session where TINAA's AI works with your IDE to design comprehensive test playbooks through guided questions and collaborative refinement.

**Parameters**:
- `project_name` (str): Name of the testing project (e.g., "E-commerce App Tests")
- `project_description` (str, optional): Description of what needs to be tested
- `target_url` (str, optional): Optional URL to analyze and test
- `existing_code_context` (str, optional): Context about existing code or project structure

**Returns**:
- `session_id`: Unique session identifier for subsequent interactions
- `status`: "started" indicating successful initialization
- `initial_questions`: List of intelligent discovery questions
- `next_step`: Guidance on what to do next

**Example Usage**:
```python
session = await start_collaborative_session(
    project_name="My Web App Tests",
    project_description="E-commerce site with user authentication",
    target_url="https://mystore.com"
)
```

### `answer_discovery_questions`

Process discovery question answers and generate intelligent test requirements and scenarios.

**Purpose**: Takes your answers to TINAA's discovery questions and uses AI to analyze them, generating comprehensive test requirements and initial test scenarios tailored to your project.

**Parameters**:
- `session_id` (str): The collaborative session ID from start_collaborative_session
- `answers` (Dict[str, str]): Dictionary mapping question IDs to your answers

**Returns**:
- `session_id`: The session identifier
- `requirements`: Structured test requirements by category
- `test_scenarios`: Initial test scenarios generated from your answers
- `next_step`: Guidance for next action

**Example Usage**:
```python
result = await answer_discovery_questions(
    session_id="abc123-def456-ghi789",
    answers={
        "app_purpose": "Online shopping platform",
        "user_journeys": "Product browsing, cart management, secure checkout",
        "browser_support": "Chrome, Firefox, Safari, Mobile Chrome",
        "auth_methods": "Email/password, Google OAuth",
        "success_criteria": "99.9% uptime, sub-2s page loads"
    }
)
```

### `refine_test_scenarios`

Refine and improve test scenarios based on collaborative feedback.

**Purpose**: Uses AI to intelligently incorporate your feedback, suggestions from your IDE, and any additional requirements to enhance the test scenarios for better coverage and quality.

**Parameters**:
- `session_id` (str): The collaborative session ID
- `scenario_feedback` (Dict[str, str]): Dictionary of scenario IDs to feedback comments
- `additional_requirements` (str, optional): Optional string with any new requirements

**Returns**:
- `session_id`: The session identifier
- `refined_scenarios`: Updated and improved test scenarios
- `next_step`: Guidance for next action

### `create_comprehensive_playbook`

Generate a comprehensive, executable test playbook from your collaborative design session.

**Purpose**: Creates a detailed, step-by-step playbook that can be executed by TINAA's automation engine, incorporating all the requirements, scenarios, and refinements from your collaborative session.

**Parameters**:
- `session_id` (str): The collaborative session ID
- `playbook_preferences` (Dict[str, Any], optional): Preferences for playbook generation

**Returns**:
- `session_id`: The session identifier
- `playbook`: Complete executable playbook with detailed steps
- `project_id`: ID of the created workspace project
- `workspace_path`: File system path to the project

### `get_session_status`

Retrieve comprehensive status and progress information for a collaborative session.

**Purpose**: Provides detailed information about your collaborative testing session including current progress, conversation history, generated artifacts, and next steps.

**Parameters**:
- `session_id` (str): The collaborative session ID to check

**Returns**:
- `session_id`: The session identifier
- `project_context`: Original project information and settings
- `test_design`: Current state of test design
- `conversation_history`: Complete history of interactions
- `context_summary`: Human-readable summary of session progress

---

## 🗂️ Workspace Management Tools

### `create_project`

Create a new Playwright testing project in TINAA's workspace with intelligent setup.

**Purpose**: Creates a new project directory with proper structure, configuration files, and optional repository cloning. Supports multiple project templates and automatic setup.

**Parameters**:
- `project_name` (str): Name for the new project
- `description` (str, optional): Description of what this project tests
- `template` (str): Project template ("basic-web-testing", "url-based-testing", "e2e-workflow")
- `repository_url` (str, optional): Optional Git repository URL to clone

**Returns**:
- `success`: Boolean indicating if project creation succeeded
- `project_id`: Unique identifier for the created project
- `path`: Absolute file system path to the project directory
- `config`: Project configuration including TINAA-specific settings

**Example Usage**:
```python
project = await create_project(
    project_name="My Store Tests",
    description="E-commerce testing suite",
    template="e2e-workflow",
    repository_url="https://github.com/myorg/test-templates"
)
```

### `create_project_from_url`

Automatically create a Playwright testing project by analyzing a target URL.

**Purpose**: TINAA analyzes the provided URL to understand the application structure, then generates an appropriate project with initial tests tailored to the discovered elements and functionality.

**Parameters**:
- `url` (str): Target URL to analyze and create tests for
- `project_name` (str, optional): Optional custom name for the project

**Returns**:
- `success`: Boolean indicating if project creation succeeded
- `project_id`: Unique identifier for the created project
- `target_url`: The URL that was analyzed
- `url_analysis`: Analysis results including detected elements
- `generated_tests`: List of automatically generated test files

### `list_projects`

Retrieve a list of all projects in TINAA's workspace with their status and metadata.

**Purpose**: Returns comprehensive information about all projects including configuration, last activity, test results, and current status.

**Returns**: List of project dictionaries with full metadata

### `get_project`

Retrieve detailed information about a specific project including configuration and status.

**Parameters**:
- `project_id` (str): Unique identifier of the project to retrieve

**Returns**: Detailed project information or None if not found

### `delete_project`

Permanently delete a project and all its files from TINAA's workspace.

**Parameters**:
- `project_id` (str): Unique identifier of the project to delete

**Returns**:
- `success`: Boolean indicating if deletion succeeded
- `message`: Confirmation or error message

### `get_workspace_status`

Get comprehensive status and statistics about TINAA's workspace and all projects.

**Purpose**: Provides workspace-wide metrics including storage usage, project counts, recent activity, and system health information.

**Returns**:
- `workspace_path`: Absolute path to workspace directory
- `total_projects`: Total number of projects
- `active_projects`: Number of active projects
- `storage_usage`: Disk space usage statistics
- `system_health`: Overall system status
- `git_status`: Git authentication status
- `ai_status`: AI provider connectivity status

### `clone_repository`

Clone a Git repository into TINAA's workspace with secure authentication.

**Purpose**: Clones a repository using available authentication methods (PAT or GitHub App), creating a new project structure with the cloned code as the base.

**Parameters**:
- `repository_url` (str): Git repository URL to clone
- `destination_name` (str, optional): Optional name for the project
- `branch` (str, optional): Optional specific branch to clone
- `auth_type` (str): Authentication method ("auto", "pat", "github_app")

**Returns**:
- `success`: Boolean indicating if clone succeeded
- `destination_path`: Local path where repository was cloned
- `branch`: Branch that was cloned
- `commit_hash`: Latest commit hash
- `auth_method`: Authentication method used

### `get_repository_info`

Fetch detailed information about a Git repository without cloning it.

**Purpose**: Uses Git provider APIs to gather repository metadata, statistics, and information useful for deciding whether to clone or integrate with a repository.

**Parameters**:
- `repository_url` (str): Git repository URL to analyze
- `auth_type` (str): Authentication method ("auto", "pat", "github_app")

**Returns**:
- `success`: Boolean indicating if info retrieval succeeded
- `name`: Repository name
- `description`: Repository description
- `language`: Primary programming language
- `stars`: Number of stars
- `private`: Whether the repository is private

---

## 🔧 Browser Automation Tools

### `start_lsp_server`

Start TINAA's Playwright Language Server Protocol (LSP) server for IDE integration.

**Purpose**: Launches a Playwright LSP server that provides intelligent code completion, diagnostics, and hover information for Playwright test code directly in your IDE.

**Parameters**:
- `tcp` (bool): Whether to use TCP mode (recommended for MCP)
- `port` (int): Port number for TCP mode server (default: 8765)

**Returns**: Status message indicating success or failure

### `test_browser_connectivity`

Test TINAA's browser automation capabilities by visiting a URL and capturing basic information.

**Purpose**: Verifies that Playwright browser automation is working correctly by navigating to a URL, capturing the page title, taking a screenshot, and reporting the results.

**Parameters**:
- `url` (str): The URL to visit for testing (default: "https://example.com")

**Returns**:
- `success`: Boolean indicating if the test passed
- `title`: Page title from the visited URL
- `status`: HTTP status code of the response
- `screenshot`: Base64-encoded screenshot of the page

### `analyze_script`

Analyze a Playwright test script for common issues, errors, and improvement opportunities.

**Purpose**: Performs static analysis on your Playwright test code to identify missing await statements, syntax issues, and potential improvements using TINAA's built-in diagnostics engine.

**Parameters**:
- `script_path` (str): Absolute path to the Playwright test script file

**Returns**:
- `script_path`: The path to the analyzed script
- `issues_found`: Number of issues detected
- `diagnostics`: List of specific issues with line numbers and descriptions

---

## 🧠 AI Assistant Tools

### `internal_problem_solving`

Get intelligent AI assistance for solving testing challenges and automation problems.

**Purpose**: TINAA's internal AI analyzes your problem and provides comprehensive solutions including implementation guidance, alternatives, and risk assessment.

**Parameters**:
- `problem_description` (str): Clear description of the problem you're facing
- `context` (Dict[str, Any], optional): Additional context like error messages or environment details
- `session_id` (str, optional): Optional session ID to include collaborative context

**Returns**:
- `problem`: The original problem description
- `solution`: Comprehensive AI-generated solution with implementation details
- `implementation_steps`: Step-by-step guidance
- `alternatives`: Alternative approaches to consider
- `risk_assessment`: Potential risks and mitigation strategies

**Example Usage**:
```python
solution = await internal_problem_solving(
    problem_description="Playwright tests fail randomly with 'element not found' errors",
    context={
        "browser": "chromium",
        "test_type": "e2e",
        "error_frequency": "30% of runs"
    }
)
```

### `collaborative_code_review`

Get comprehensive AI-powered code review for your Playwright test code with collaborative insights.

**Purpose**: TINAA's AI analyzes your test code for quality, best practices, performance, security, and maintainability, providing actionable feedback and improvement suggestions.

**Parameters**:
- `code` (str): The Playwright test code to review
- `review_focus` (str): Focus area ("general", "performance", "security", "accessibility", "maintainability")
- `session_id` (str, optional): Optional session ID to include collaborative context

**Returns**:
- `code_reviewed`: Summary of the reviewed code
- `review_focus`: The focus area that was analyzed
- `analysis`: Detailed AI analysis with specific findings
- `quality_score`: Overall code quality score (1-10)
- `improvement_areas`: Specific areas for improvement

---

## Resource Endpoints

TINAA also provides MCP resources for accessing structured information:

### `tinaa://sessions/{session_id}`
Get session information as a resource for a specific collaborative session.

### `tinaa://templates/discovery-questions`
Get the discovery questions template with all available question categories.

### `tinaa://prompts/internal-problem-solving`
Get internal problem-solving prompts and guidance templates.

---

## Integration Examples

### Basic IDE Integration

```typescript
// Configure TINAA MCP in your IDE
const tinaa = new MCPClient("tinaa", {
  command: "python",
  args: ["/path/to/tinaa/app/tinaa_mcp_server.py"]
});

// Start a collaborative session
const session = await tinaa.call("start_collaborative_session", {
  project_name: "My Web App Tests",
  target_url: "https://myapp.com"
});

// Get workspace status
const status = await tinaa.call("get_workspace_status");
console.log(`Total projects: ${status.total_projects}`);
```

### Advanced Collaborative Workflow

```typescript
// 1. Start collaborative session
const session = await tinaa.call("start_collaborative_session", {
  project_name: "E-commerce Testing Suite",
  project_description: "Comprehensive testing for online store",
  target_url: "https://shop.example.com"
});

// 2. Answer discovery questions
const requirements = await tinaa.call("answer_discovery_questions", {
  session_id: session.session_id,
  answers: {
    app_purpose: "E-commerce platform with user accounts",
    user_journeys: "Browse, search, cart, checkout, account management",
    browser_support: "Chrome, Firefox, Safari, Mobile browsers",
    auth_methods: "Email/password, social login, guest checkout",
    success_criteria: "Zero critical bugs, <2s page loads"
  }
});

// 3. Refine scenarios based on IDE analysis
const refined = await tinaa.call("refine_test_scenarios", {
  session_id: session.session_id,
  scenario_feedback: {
    checkout_test: "Add payment method validation",
    mobile_test: "Include responsive design checks"
  },
  additional_requirements: "Must support international shipping"
});

// 4. Generate executable playbook
const playbook = await tinaa.call("create_comprehensive_playbook", {
  session_id: session.session_id,
  playbook_preferences: {
    automation_level: "high",
    test_types: ["functional", "accessibility", "performance"],
    reporting: "detailed"
  }
});

// 5. Create project from playbook
console.log(`Playbook created with ${playbook.playbook.steps.length} steps`);
```

## Error Handling

All TINAA MCP tools follow consistent error handling patterns:

```typescript
try {
  const result = await tinaa.call("create_project", {
    project_name: "My Tests",
    template: "basic-web-testing"
  });
  
  if (!result.success) {
    console.error(`Project creation failed: ${result.error}`);
    return;
  }
  
  console.log(`Project created: ${result.project_id}`);
} catch (error) {
  console.error(`MCP tool error: ${error.message}`);
}
```

## Best Practices

### 1. Session Management
- Always check session status before continuing collaborative workflows
- Store session IDs for multi-step processes
- Handle session timeouts gracefully

### 2. Error Recovery
- Validate inputs before calling tools
- Implement retry logic for network-dependent operations
- Provide meaningful error messages to users

### 3. Performance Optimization
- Use `get_workspace_status` to check system health before intensive operations
- Monitor storage usage for large projects
- Cache repository information when possible

### 4. Security
- Never expose API keys or credentials in tool parameters
- Use secure authentication methods for Git operations
- Validate and sanitize user inputs

This comprehensive reference covers all TINAA MCP tools with detailed documentation following FastMCP 2.8.0 standards, enabling seamless integration with LLM-enabled IDEs for intelligent collaborative testing.