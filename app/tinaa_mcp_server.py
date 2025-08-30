#!/usr/bin/env python3
"""
TINAA MCP Server

Exposes TINAA's testing capabilities as an MCP server for IDE integration.
Enables collaborative test design between TINAA AI and IDE LLMs.
"""

import asyncio
import json
import logging

# Import collaborative prompts
import sys
from datetime import datetime
from typing import Optional, Any

from fastmcp import Context, FastMCP

from app.ai_integration import AIManager
from app.workspace_manager import WorkspaceManager

import os
# Add prompts directory to path (relative to this file)
prompts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")
if os.path.exists(prompts_dir):
    sys.path.append(prompts_dir)
from collaborative_prompts import CollaborativePrompts

logger = logging.getLogger("tinaa.mcp_server")

# Initialize TINAA MCP Server
tinaa_mcp = FastMCP("TINAA - Testing Intelligence Network Automation Assistant")

# Global instances
ai_manager = None
workspace_manager = None


class CollaborativeSession:
    """Manages collaborative test design sessions between TINAA and IDE"""

    def __init__(self, session_id: str, project_context: dict[str, Any]):
        self.session_id = session_id
        self.project_context = project_context
        self.conversation_history: list[dict[str, Any]] = []
        self.test_design: dict[str, Any] = {
            "requirements": {},
            "test_scenarios": [],
            "current_playbook": None,
            "design_decisions": [],
            "questions_answered": [],
        }
        self.created_at = datetime.now()

    def add_interaction(self, source: str, message: str, data: Optional[dict ] = None):
        """Add an interaction to the session history"""
        self.conversation_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "source": source,  # "tinaa", "ide", "user"
                "message": message,
                "data": data or {},
            }
        )

    def update_design(self, key: str, value: Any):
        """Update the test design"""
        self.test_design[key] = value

    def get_context_summary(self) -> str:
        """Get a summary of the current session context"""
        return f"""
Session: {self.session_id}
Project: {self.project_context.get('name', 'Unknown')}
Interactions: {len(self.conversation_history)}
Test Scenarios: {len(self.test_design['test_scenarios'])}
Requirements Gathered: {len(self.test_design['requirements'])}
Current Status: {"Active" if len(self.conversation_history) > 0 else "Initialized"}
"""


# Session storage
active_sessions: dict[str, CollaborativeSession] = {}


async def initialize_global_components():
    """Initialize global AI manager and workspace manager"""
    global ai_manager, workspace_manager

    if not ai_manager:
        ai_manager = AIManager()
        # Initialize AI providers from secrets manager
        await ai_manager.initialize_from_secrets()

    if not workspace_manager:
        workspace_manager = WorkspaceManager()


# MCP Tools for IDE Integration


@tinaa_mcp.tool()
async def start_collaborative_session(
    project_name: str,
    project_description: str = "",
    target_url: Optional[str ] = None,
    existing_code_context: Optional[str ] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """
    Start a collaborative test design session between TINAA and your IDE for intelligent test planning.

    This tool initiates an interactive session where TINAA's AI works with your IDE to design
    comprehensive test playbooks through guided questions and collaborative refinement.

    Args:
        project_name: Name of the testing project (e.g., "E-commerce App Tests")
        project_description: Description of what needs to be tested (e.g., "Testing checkout flow and user registration")
        target_url: Optional URL to analyze and test (e.g., "https://myapp.com")
        existing_code_context: Optional context about existing code or project structure
        ctx: Execution context (automatically provided by FastMCP)

    Returns:
        Dict containing:
        - session_id: Unique session identifier for subsequent interactions
        - status: "started" indicating successful initialization
        - initial_questions: List of intelligent discovery questions to understand requirements
        - next_step: Guidance on what to do next ("answer_discovery_questions")

    Example:
        >>> session = await start_collaborative_session(
        ...     project_name="My Web App Tests",
        ...     project_description="E-commerce site with user authentication",
        ...     target_url="https://mystore.com"
        ... )
        >>> print(session["session_id"])
        "abc123-def456-ghi789"
    """
    await initialize_global_components()

    if ctx:
        await ctx.info(f"Starting collaborative session for project: {project_name}")

    import uuid

    session_id = str(uuid.uuid4())

    project_context = {
        "name": project_name,
        "description": project_description,
        "target_url": target_url,
        "existing_code": existing_code_context,
        "session_id": session_id,
    }

    session = CollaborativeSession(session_id, project_context)
    active_sessions[session_id] = session

    # Generate initial questions to understand requirements
    initial_questions = await _generate_discovery_questions(project_context)

    session.add_interaction(
        "tinaa", "Session started", {"questions": initial_questions}
    )

    logger.info(f"Started collaborative session {session_id} for {project_name}")

    return {
        "session_id": session_id,
        "status": "started",
        "initial_questions": initial_questions,
        "next_step": "answer_discovery_questions",
    }


@tinaa_mcp.tool()
async def answer_discovery_questions(
    session_id: str, answers: dict[str, str], ctx: Context = None
) -> dict[str, Any]:
    """
    Process discovery question answers and generate intelligent test requirements and scenarios.

    Takes your answers to TINAA's discovery questions and uses AI to analyze them, generating
    comprehensive test requirements and initial test scenarios tailored to your project.

    Args:
        session_id: The collaborative session ID from start_collaborative_session
        answers: Dictionary mapping question IDs to your answers (e.g., {"app_purpose": "E-commerce platform", "user_journeys": "Browse, cart, checkout"})
        ctx: Execution context (automatically provided by FastMCP)

    Returns:
        Dict containing:
        - session_id: The session identifier
        - requirements: Structured test requirements organized by category (functional, technical, performance, security, accessibility)
        - test_scenarios: Initial test scenarios generated from your answers
        - next_step: Guidance for next action ("refine_scenarios_or_create_playbook")

    Example:
        >>> result = await answer_discovery_questions(
        ...     session_id="abc123-def456-ghi789",
        ...     answers={
        ...         "app_purpose": "Online shopping platform",
        ...         "user_journeys": "Product browsing, cart management, secure checkout",
        ...         "browser_support": "Chrome, Firefox, Safari, Mobile Chrome",
        ...         "auth_methods": "Email/password, Google OAuth",
        ...         "success_criteria": "99.9% uptime, sub-2s page loads"
        ...     }
        ... )
        >>> len(result["test_scenarios"])
        12
    """
    await initialize_global_components()

    if session_id not in active_sessions:
        raise Exception(f"Session {session_id} not found")

    session = active_sessions[session_id]

    if ctx:
        await ctx.info(f"Processing discovery answers for session {session_id}")

    # Store answers
    session.update_design("questions_answered", answers)
    session.add_interaction(
        "user", "Answered discovery questions", {"answers": answers}
    )

    # Analyze answers and generate test requirements using collaborative prompts
    requirements = await _analyze_answers_and_generate_requirements(session, answers)
    session.update_design("requirements", requirements)

    # Generate initial test scenarios based on requirements using collaborative prompts
    test_scenarios = await _generate_test_scenarios(session, requirements)
    session.update_design("test_scenarios", test_scenarios)

    session.add_interaction(
        "tinaa",
        "Generated requirements and scenarios",
        {"requirements": requirements, "scenarios": test_scenarios},
    )

    return {
        "session_id": session_id,
        "requirements": requirements,
        "test_scenarios": test_scenarios,
        "next_step": "refine_scenarios_or_create_playbook",
    }


@tinaa_mcp.tool()
async def refine_test_scenarios(
    session_id: str,
    scenario_feedback: dict[str, str],
    additional_requirements: Optional[str ] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """
    Refine and improve test scenarios based on collaborative feedback from you and your IDE.

    Uses AI to intelligently incorporate your feedback, suggestions from your IDE, and any
    additional requirements to enhance the test scenarios for better coverage and quality.

    Args:
        session_id: The collaborative session ID from your active session
        scenario_feedback: Dictionary of scenario IDs to feedback comments (e.g., {"scenario_1": "Add edge case for empty cart", "scenario_3": "Include mobile-specific tests"})
        additional_requirements: Optional string with any new requirements discovered (e.g., "Need to test with different payment methods")
        ctx: Execution context (automatically provided by FastMCP)

    Returns:
        Dict containing:
        - session_id: The session identifier
        - refined_scenarios: Updated and improved test scenarios incorporating all feedback
        - next_step: Guidance for next action ("create_comprehensive_playbook")

    Example:
        >>> result = await refine_test_scenarios(
        ...     session_id="abc123-def456-ghi789",
        ...     scenario_feedback={
        ...         "login_test": "Add two-factor authentication scenario",
        ...         "checkout_test": "Include guest checkout option",
        ...         "performance_test": "Test with 1000 concurrent users"
        ...     },
        ...     additional_requirements="Must support international payment methods"
        ... )
        >>> len(result["refined_scenarios"])
        15
    """
    await initialize_global_components()

    if session_id not in active_sessions:
        raise Exception(f"Session {session_id} not found")

    session = active_sessions[session_id]

    if ctx:
        await ctx.info(f"Refining test scenarios for session {session_id}")

    session.add_interaction(
        "ide",
        "Provided scenario feedback",
        {
            "feedback": scenario_feedback,
            "additional_requirements": additional_requirements,
        },
    )

    # Use AI to refine scenarios based on feedback
    refined_scenarios = await _refine_scenarios_with_ai(
        session, scenario_feedback, additional_requirements
    )
    session.update_design("test_scenarios", refined_scenarios)

    session.add_interaction(
        "tinaa", "Refined test scenarios", {"scenarios": refined_scenarios}
    )

    return {
        "session_id": session_id,
        "refined_scenarios": refined_scenarios,
        "next_step": "create_comprehensive_playbook",
    }


@tinaa_mcp.tool()
async def create_comprehensive_playbook(
    session_id: str,
    playbook_preferences: Optional[dict[str, Any] ] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """
    Generate a comprehensive, executable test playbook from your collaborative design session.

    Creates a detailed, step-by-step playbook that can be executed by TINAA's automation engine,
    incorporating all the requirements, scenarios, and refinements from your collaborative session.

    Args:
        session_id: The collaborative session ID from your active session
        playbook_preferences: Optional preferences for playbook generation (e.g., {"automation_level": "high", "test_types": ["functional", "performance"], "browser_coverage": ["chrome", "firefox"]})
        ctx: Execution context (automatically provided by FastMCP)

    Returns:
        Dict containing:
        - session_id: The session identifier
        - playbook: Complete executable playbook with detailed steps, parameters, and validation points
        - project_id: ID of the created workspace project
        - workspace_path: File system path to the project
        - next_step: Guidance for next action ("execute_or_export_playbook")

    The playbook includes:
        - Setup and teardown phases
        - Detailed test steps with Playwright actions
        - Error handling and retry logic
        - Performance monitoring points
        - Accessibility validation checks
        - Cross-browser compatibility tests

    Example:
        >>> playbook = await create_comprehensive_playbook(
        ...     session_id="abc123-def456-ghi789",
        ...     playbook_preferences={
        ...         "automation_level": "high",
        ...         "test_types": ["functional", "accessibility", "performance"],
        ...         "reporting": "detailed",
        ...         "parallel_execution": True
        ...     }
        ... )
        >>> len(playbook["playbook"]["steps"])
        45
    """
    await initialize_global_components()

    if session_id not in active_sessions:
        raise Exception(f"Session {session_id} not found")

    session = active_sessions[session_id]

    if ctx:
        await ctx.info(f"Creating comprehensive playbook for session {session_id}")

    # Generate comprehensive playbook using collaborative prompts
    playbook_prompt = CollaborativePrompts.playbook_generation_prompt(
        project_context=session.project_context,
        requirements=session.test_design["requirements"],
        scenarios=session.test_design["test_scenarios"],
        conversation_history=session.conversation_history[-5:],  # Last 5 interactions
    )

    # Use AI manager to generate playbook with specialized prompt
    playbook_response = await ai_manager.chat_completion(playbook_prompt)
    playbook = json.loads(playbook_response)

    session.update_design("current_playbook", playbook)
    session.add_interaction(
        "tinaa", "Generated comprehensive playbook", {"playbook": playbook}
    )

    # Create actual project in workspace
    project_result = await workspace_manager.create_project(
        name=session.project_context["name"],
        description=session.project_context["description"],
        template="collaborative-design",
    )

    return {
        "session_id": session_id,
        "playbook": playbook,
        "project_id": project_result.get("project_id"),
        "workspace_path": project_result.get("path"),
        "next_step": "execute_or_export_playbook",
    }


@tinaa_mcp.tool()
async def get_session_status(session_id: str, ctx: Context = None) -> dict[str, Any]:
    """
    Retrieve comprehensive status and progress information for a collaborative session.

    Provides detailed information about your collaborative testing session including current progress,
    conversation history, generated artifacts, and next steps.

    Args:
        session_id: The collaborative session ID to check status for
        ctx: Execution context (automatically provided by FastMCP)

    Returns:
        Dict containing:
        - session_id: The session identifier
        - project_context: Original project information and settings
        - test_design: Current state of test design including requirements and scenarios
        - conversation_history: Complete history of interactions in the session
        - context_summary: Human-readable summary of session progress and status
        - progress_indicators: Percentage completion of different design phases

    Example:
        >>> status = await get_session_status("abc123-def456-ghi789")
        >>> print(status["context_summary"])
        "Session: abc123-def456-ghi789
        Project: My Web App Tests
        Interactions: 8
        Test Scenarios: 12
        Requirements Gathered: 15
        Current Status: Active"
    """
    if session_id not in active_sessions:
        raise Exception(f"Session {session_id} not found")

    session = active_sessions[session_id]

    return {
        "session_id": session_id,
        "project_context": session.project_context,
        "test_design": session.test_design,
        "conversation_history": session.conversation_history,
        "context_summary": session.get_context_summary(),
    }


@tinaa_mcp.tool()
async def internal_problem_solving(
    problem_description: str,
    context: Optional[dict[str, Any] ] = None,
    session_id: Optional[str ] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """
    Get intelligent AI assistance for solving testing challenges and automation problems.

    TINAA's internal AI analyzes your problem and provides comprehensive solutions including
    implementation guidance, alternatives, and risk assessment. Perfect for debugging tests,
    optimizing automation strategies, or solving complex testing challenges.

    Args:
        problem_description: Clear description of the problem you're facing (e.g., "My Playwright tests are flaky on mobile devices" or "Need to test file upload functionality")
        context: Optional additional context like error messages, code snippets, or environment details
        session_id: Optional session ID to include collaborative session context in the analysis
        ctx: Execution context (automatically provided by FastMCP)

    Returns:
        Dict containing:
        - problem: The original problem description
        - solution: Comprehensive AI-generated solution with implementation details
        - context_used: Context information that was considered in the analysis
        - timestamp: When the analysis was performed
        - implementation_steps: Step-by-step guidance for implementing the solution
        - alternatives: Alternative approaches to consider
        - risk_assessment: Potential risks and mitigation strategies

    Example:
        >>> solution = await internal_problem_solving(
        ...     problem_description="Playwright tests fail randomly with 'element not found' errors",
        ...     context={
        ...         "browser": "chromium",
        ...         "test_type": "e2e",
        ...         "error_frequency": "30% of runs"
        ...     }
        ... )
        >>> print(solution["solution"])
        "The random 'element not found' errors suggest timing issues..."
    """
    await initialize_global_components()

    if ctx:
        await ctx.info(f"Solving problem: {problem_description[:100]}...")

    # Build context for problem solving
    full_context = context or {}

    if session_id and session_id in active_sessions:
        session = active_sessions[session_id]
        full_context.update(
            {
                "session_context": session.project_context,
                "current_design": session.test_design,
                "recent_interactions": session.conversation_history[-3:],
            }
        )

    # Use collaborative prompt for problem solving
    problem_solving_prompt = CollaborativePrompts.problem_solving_prompt(
        problem_description=problem_description,
        context=full_context,
        session_context=full_context.get("session_context"),
    )

    solution = await ai_manager.chat_completion(problem_solving_prompt)

    result = {
        "problem": problem_description,
        "solution": solution,
        "context_used": full_context,
        "timestamp": datetime.now().isoformat(),
    }

    # Log to session if provided
    if session_id and session_id in active_sessions:
        session = active_sessions[session_id]
        session.add_interaction(
            "tinaa", f"Solved problem: {problem_description}", result
        )

    return result


@tinaa_mcp.tool()
async def collaborative_code_review(
    code: str,
    review_focus: str = "general",
    session_id: Optional[str ] = None,
    ctx: Context = None,
) -> dict[str, Any]:
    """
    Get comprehensive AI-powered code review for your Playwright test code with collaborative insights.

    TINAA's AI analyzes your test code for quality, best practices, performance, security, and
    maintainability, providing actionable feedback and improvement suggestions.

    Args:
        code: The Playwright test code to review (TypeScript or JavaScript)
        review_focus: Focus area for the review - "general" (overall quality), "performance" (speed and efficiency), "security" (safety and data protection), "accessibility" (a11y compliance), or "maintainability" (long-term code health)
        session_id: Optional session ID to include collaborative context in the review
        ctx: Execution context (automatically provided by FastMCP)

    Returns:
        Dict containing:
        - code_reviewed: Summary of the reviewed code (truncated for large files)
        - review_focus: The focus area that was analyzed
        - analysis: Detailed AI analysis with specific findings and recommendations
        - session_context: Any collaborative session context that was considered
        - timestamp: When the review was performed
        - quality_score: Overall code quality score (1-10)
        - improvement_areas: Specific areas for improvement
        - collaboration_opportunities: Ways your IDE can assist with improvements

    Example:
        >>> review = await collaborative_code_review(
        ...     code='''
        ...     test('login flow', async ({ page }) => {
        ...       await page.goto('/login');
        ...       await page.click('#submit');
        ...     });
        ...     ''',
        ...     review_focus="performance"
        ... )
        >>> print(review["analysis"]["quality_score"])
        6
    """
    await initialize_global_components()

    if ctx:
        await ctx.info(f"Performing {review_focus} code review")

    # Get context from session if available
    session_context = {}
    if session_id and session_id in active_sessions:
        session = active_sessions[session_id]
        session_context = {
            "project": session.project_context,
            "requirements": session.test_design.get("requirements", {}),
        }

    # Use collaborative prompt for code review
    code_review_prompt = CollaborativePrompts.code_review_prompt(
        code=code, review_focus=review_focus, project_context=session_context
    )

    analysis = await ai_manager.chat_completion(code_review_prompt)

    result = {
        "code_reviewed": code[:200] + "..." if len(code) > 200 else code,
        "review_focus": review_focus,
        "analysis": analysis,
        "session_context": session_context,
        "timestamp": datetime.now().isoformat(),
    }

    if session_id and session_id in active_sessions:
        session = active_sessions[session_id]
        session.add_interaction(
            "tinaa", f"Code review completed ({review_focus})", result
        )

    return result


# Import and register workspace management tools

# Note: Workspace tools are already registered with their own MCP instance
# They don't need to be re-registered with tinaa_mcp

# MCP Resources


@tinaa_mcp.resource("tinaa://sessions/{session_id}")
def get_session_resource(session_id: str) -> str:
    """
    Get comprehensive session information as a structured resource.

    Provides detailed information about a collaborative session including project context,
    design progress, and conversation history in a structured JSON format.

    Args:
        session_id: The collaborative session ID to retrieve information for

    Returns:
        JSON string containing session data or error message if session not found
    """
    if session_id not in active_sessions:
        return f"Session {session_id} not found"

    session = active_sessions[session_id]
    return json.dumps(
        {
            "session": session.project_context,
            "design": session.test_design,
            "history": session.conversation_history,
            "status": session.get_context_summary(),
            "created_at": session.created_at.isoformat(),
        },
        indent=2,
    )


@tinaa_mcp.resource("tinaa://templates/discovery-questions")
def get_discovery_questions_template() -> str:
    """
    Get the comprehensive discovery questions template for collaborative test design.

    Provides structured question categories used by TINAA to understand project requirements
    and generate appropriate test scenarios during collaborative sessions.

    Returns:
        JSON string containing categorized discovery questions for different aspects of testing
    """
    return json.dumps(
        {
            "project_understanding": [
                "What is the main purpose of the application/website being tested?",
                "What are the critical user journeys that must work?",
                "Are there any specific browsers or devices to support?",
                "What is the expected user load or performance requirements?",
            ],
            "technical_details": [
                "What authentication methods are used?",
                "Are there API integrations that need testing?",
                "What databases or external services are involved?",
                "Are there any known technical constraints or limitations?",
            ],
            "business_requirements": [
                "What are the acceptance criteria for this testing project?",
                "What constitutes a critical failure vs. minor issue?",
                "What is the timeline and delivery expectations?",
                "Who are the stakeholders and how should results be reported?",
            ],
            "quality_attributes": [
                "What accessibility standards need to be met (WCAG, ADA)?",
                "Are there specific security requirements or compliance needs?",
                "What performance benchmarks are expected?",
                "How important is cross-browser compatibility?",
            ],
            "automation_preferences": [
                "What level of test automation is desired?",
                "Are there existing testing frameworks or tools in use?",
                "How should test results be reported and integrated?",
                "What is the maintenance strategy for automated tests?",
            ],
        },
        indent=2,
    )


@tinaa_mcp.resource("tinaa://prompts/internal-problem-solving")
def get_internal_prompts() -> str:
    """
    Get comprehensive internal problem-solving prompts and guidance templates.

    Provides structured templates and approaches used by TINAA's AI for solving
    various testing challenges, debugging issues, and optimizing test automation.

    Returns:
        Markdown-formatted guide containing problem-solving approaches and templates
    """
    return """# TINAA Internal Problem-Solving Prompts and Guidance

## 🎯 Test Design Analysis

### Requirements Analysis
- **User Story Decomposition**: Break down user stories into testable scenarios
- **Acceptance Criteria Validation**: Ensure all criteria have corresponding tests
- **Edge Case Identification**: Systematically identify boundary conditions
- **Risk-Based Prioritization**: Focus testing effort on high-risk areas

### Test Coverage Assessment
- **Functional Coverage**: Verify all features have adequate test coverage
- **Path Coverage**: Ensure all user journeys are tested
- **Data Coverage**: Test with various data sets and edge cases
- **Browser/Device Coverage**: Plan cross-platform testing strategy

### Automation Strategy
- **ROI Analysis**: Identify tests with highest automation value
- **Maintenance Considerations**: Balance automation with maintainability
- **Parallel Execution**: Design tests for concurrent execution
- **CI/CD Integration**: Plan automation pipeline integration

## 🔧 Code Quality Assessment

### Playwright Best Practices
- **Selector Strategy**: Use stable, maintainable selectors
- **Wait Strategies**: Implement proper waiting mechanisms
- **Page Object Model**: Structure tests for reusability
- **Test Independence**: Ensure tests can run in isolation

### Performance Optimization
- **Test Execution Speed**: Minimize unnecessary waits and operations
- **Resource Usage**: Optimize browser and system resource consumption
- **Parallel Testing**: Design for parallel execution capabilities
- **Test Data Management**: Efficient test data setup and teardown

### Maintainability Improvements
- **Code Organization**: Structure tests logically and consistently
- **Documentation**: Ensure tests are well-documented and understandable
- **Reusability**: Create reusable components and utilities
- **Version Control**: Implement proper versioning strategies

## 🐛 Debugging Assistance

### Test Failure Analysis
- **Root Cause Investigation**: Systematic approach to failure diagnosis
- **Environment Factors**: Consider environmental influences on test results
- **Timing Issues**: Identify and resolve race conditions
- **Data Dependencies**: Analyze test data-related failures

### Debugging Strategies
- **Logging and Tracing**: Implement comprehensive logging strategies
- **Visual Debugging**: Use screenshots and videos for debugging
- **Browser DevTools**: Leverage browser debugging capabilities
- **Test Isolation**: Isolate failing tests for focused debugging

### Preventive Measures
- **Monitoring**: Implement test health monitoring
- **Early Warning Systems**: Set up alerts for test degradation
- **Regular Maintenance**: Schedule regular test review and updates
- **Knowledge Sharing**: Document common issues and solutions

## 🔄 Integration Planning

### CI/CD Pipeline Integration
- **Pipeline Design**: Structure testing phases in deployment pipeline
- **Trigger Strategies**: Define when and how tests should execute
- **Reporting Integration**: Integrate test results with build reports
- **Failure Handling**: Plan response strategies for test failures

### Test Data Management
- **Data Setup**: Automated test data preparation strategies
- **Data Isolation**: Ensure test data doesn't interfere between tests
- **Data Cleanup**: Proper test data cleanup procedures
- **Environment Management**: Manage test data across environments

### Monitoring and Reporting
- **Metrics Collection**: Define and collect relevant test metrics
- **Dashboard Design**: Create informative test status dashboards
- **Alerting Systems**: Set up appropriate alerting for test issues
- **Trend Analysis**: Monitor test performance and reliability trends

## 🚀 Advanced Problem-Solving Patterns

### Flaky Test Resolution
1. **Identify Pattern**: Analyze when and why tests become flaky
2. **Stabilize**: Implement proper waits and error handling
3. **Monitor**: Track flakiness metrics over time
4. **Iterate**: Continuously improve test stability

### Performance Issue Resolution
1. **Measure**: Establish baseline performance metrics
2. **Identify Bottlenecks**: Use profiling to find slow operations
3. **Optimize**: Apply targeted optimizations
4. **Validate**: Confirm improvements with metrics

### Cross-Browser Issue Resolution
1. **Isolate**: Identify browser-specific behaviors
2. **Adapt**: Implement browser-specific handling
3. **Abstract**: Create browser-agnostic abstractions
4. **Test**: Validate across all target browsers

### API Integration Testing
1. **Mock Strategy**: Determine when to mock vs. use real APIs
2. **Contract Testing**: Ensure API contracts are maintained
3. **Error Simulation**: Test API failure scenarios
4. **Performance Testing**: Validate API performance under load

## 📋 Problem-Solving Checklist

### Before Starting
- [ ] Clearly define the problem and success criteria
- [ ] Gather all relevant context and error information
- [ ] Identify stakeholders and communication needs
- [ ] Set realistic timeline expectations

### During Investigation
- [ ] Document findings and attempted solutions
- [ ] Test hypotheses systematically
- [ ] Consider multiple potential causes
- [ ] Collaborate with team members when appropriate

### After Resolution
- [ ] Document the solution for future reference
- [ ] Update preventive measures if applicable
- [ ] Share learnings with the team
- [ ] Monitor to ensure the issue doesn't recur

This comprehensive guide provides structured approaches to common testing challenges and serves as a reference for TINAA's AI-powered problem-solving capabilities."""


# Helper functions


async def _generate_discovery_questions(
    project_context: dict[str, Any],
) -> list[dict[str, str]]:
    """Generate intelligent discovery questions based on project context"""
    await initialize_global_components()

    base_questions = [
        {
            "id": "app_purpose",
            "question": "What is the primary purpose and main functionality of the application?",
            "category": "understanding",
        },
        {
            "id": "user_journeys",
            "question": "What are the most critical user journeys that absolutely must work?",
            "category": "requirements",
        },
        {
            "id": "browser_support",
            "question": "Which browsers and devices need to be supported?",
            "category": "technical",
        },
        {
            "id": "auth_methods",
            "question": "What authentication and authorization methods are used?",
            "category": "technical",
        },
        {
            "id": "success_criteria",
            "question": "What defines success for this testing project?",
            "category": "business",
        },
    ]

    # Use AI to generate additional context-specific questions
    if ai_manager and ai_manager.active_provider:
        additional_prompt = f"""
        Based on this project context: {json.dumps(project_context, indent=2)}
        
        Generate 3 additional specific discovery questions that would help understand
        the unique testing requirements for this project. Format as JSON array with
        id, question, and category fields.
        """

        try:
            ai_response = await ai_manager.chat_completion(additional_prompt)
            additional_questions = json.loads(ai_response)
            if isinstance(additional_questions, list):
                base_questions.extend(additional_questions)
        except Exception as e:
            logger.warning(f"Could not generate additional questions: {e}")

    return base_questions


async def _analyze_answers_and_generate_requirements(
    session: CollaborativeSession, answers: dict[str, str]
) -> dict[str, Any]:
    """Analyze discovery answers and generate test requirements using collaborative prompts"""
    await initialize_global_components()

    requirements = {
        "functional": [],
        "technical": [],
        "performance": [],
        "security": [],
        "accessibility": [],
        "cross_browser": [],
    }

    if ai_manager and ai_manager.active_provider:
        # Use collaborative prompt for analysis
        analysis_prompt = CollaborativePrompts.discovery_analysis_prompt(
            project_context=session.project_context, answers=answers
        )

        try:
            ai_response = await ai_manager.chat_completion(analysis_prompt)
            ai_requirements = json.loads(ai_response)
            requirements.update(ai_requirements)

            logger.info("Generated requirements using collaborative AI analysis")
        except Exception as e:
            logger.warning(f"Could not generate AI requirements: {e}")
            # Fallback to basic requirements structure

    return requirements


async def _generate_test_scenarios(
    session: CollaborativeSession, requirements: dict[str, Any]
) -> list[dict[str, Any]]:
    """Generate test scenarios based on requirements using collaborative prompts"""
    await initialize_global_components()

    scenarios = []

    if ai_manager and ai_manager.active_provider:
        # Use collaborative prompt for scenario generation
        scenario_prompt = CollaborativePrompts.scenario_generation_prompt(
            requirements=requirements, project_context=session.project_context
        )

        try:
            ai_response = await ai_manager.chat_completion(scenario_prompt)
            scenarios = json.loads(ai_response)

            logger.info(
                f"Generated {len(scenarios)} test scenarios using collaborative AI"
            )
        except Exception as e:
            logger.warning(f"Could not generate AI scenarios: {e}")
            # Fallback to basic scenarios
            scenarios = [
                {
                    "id": "basic_navigation",
                    "name": "Basic Navigation Test",
                    "description": "Test basic page navigation and loading",
                    "priority": "high",
                    "category": "functional",
                    "steps": [
                        "Navigate to homepage",
                        "Verify page loads",
                        "Check navigation menu",
                    ],
                    "expected_outcome": "All pages load successfully",
                    "validation_points": [
                        "Page title is correct",
                        "Navigation menu is visible",
                    ],
                    "automation_potential": "high",
                }
            ]

    return scenarios


async def _refine_scenarios_with_ai(
    session: CollaborativeSession,
    feedback: dict[str, str],
    additional_requirements: Optional[str ],
) -> list[dict[str, Any]]:
    """Refine scenarios based on feedback using collaborative prompts"""
    await initialize_global_components()

    current_scenarios = session.test_design.get("test_scenarios", [])

    if ai_manager and ai_manager.active_provider:
        # Use collaborative prompt for scenario refinement
        refinement_prompt = CollaborativePrompts.scenario_refinement_prompt(
            current_scenarios=current_scenarios,
            feedback=feedback,
            additional_requirements=additional_requirements,
        )

        try:
            ai_response = await ai_manager.chat_completion(refinement_prompt)
            refined_scenarios = json.loads(ai_response)

            logger.info(
                f"Refined {len(refined_scenarios)} scenarios using collaborative AI feedback"
            )
            return refined_scenarios
        except Exception as e:
            logger.warning(f"Could not refine scenarios with AI: {e}")

    return current_scenarios


def _get_review_focus_criteria(focus: str) -> str:
    """Get criteria for different review focus areas"""
    criteria = {
        "general": """
        - Code organization and structure
        - Readability and maintainability
        - Proper use of Playwright APIs
        - Error handling and robustness
        """,
        "performance": """
        - Efficient selector strategies
        - Proper wait strategies
        - Resource usage optimization
        - Parallel execution opportunities
        """,
        "security": """
        - Secure credential handling
        - Input validation testing
        - Authentication/authorization testing
        - Data exposure risks
        """,
        "testing": """
        - Test coverage completeness
        - Test isolation and independence
        - Assertion quality and coverage
        - Test data management
        """,
    }

    return criteria.get(focus, criteria["general"])


# Initialize and expose the server
async def start_tinaa_mcp_server():
    """Start the TINAA MCP server"""
    await initialize_global_components()
    logger.info("TINAA MCP Server initialized and ready for IDE integration")
    return tinaa_mcp


if __name__ == "__main__":
    # For testing the MCP server directly
    asyncio.run(start_tinaa_mcp_server())
