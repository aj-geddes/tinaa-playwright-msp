#!/usr/bin/env python3
"""
TINAA Collaborative MCP Prompts

Intelligent prompts for guided testing playbook generation and
collaborative design between TINAA and IDE LLMs.
"""

import json
from typing import Any


class CollaborativePrompts:
    """Prompts for collaborative test design sessions"""

    @staticmethod
    def discovery_analysis_prompt(
        project_context: dict[str, Any], answers: dict[str, str]
    ) -> str:
        """Generate prompt for analyzing discovery question answers"""
        return f"""
As TINAA's intelligent test planning assistant, analyze these discovery question answers to generate comprehensive test requirements.

PROJECT CONTEXT:
{json.dumps(project_context, indent=2)}

USER ANSWERS:
{json.dumps(answers, indent=2)}

Based on these answers, generate a structured analysis that includes:

1. **FUNCTIONAL REQUIREMENTS**
   - Core features that must be tested
   - User workflows and journeys
   - Business logic validation points
   - Data handling requirements

2. **TECHNICAL REQUIREMENTS**
   - Browser/device compatibility needs
   - Performance benchmarks
   - API integration testing needs
   - Authentication/authorization testing

3. **QUALITY ATTRIBUTES**
   - Accessibility compliance levels
   - Security testing priorities
   - Usability testing focus areas
   - Reliability and robustness needs

4. **TEST STRATEGY RECOMMENDATIONS**
   - Suggested test automation approach
   - Manual vs automated test distribution
   - Risk-based testing priorities
   - Continuous integration considerations

5. **COLLABORATION OPPORTUNITIES**
   - Areas where IDE assistance would be valuable
   - Code generation opportunities
   - Automated analysis possibilities
   - Real-time feedback mechanisms

Format your response as a structured JSON object that can be used by both TINAA and the IDE for further collaborative planning.

Focus on creating actionable, specific requirements that will lead to effective test scenarios.
"""

    @staticmethod
    def scenario_generation_prompt(
        requirements: dict[str, Any], project_context: dict[str, Any]
    ) -> str:
        """Generate prompt for creating test scenarios"""
        return f"""
As TINAA's test scenario architect, create comprehensive test scenarios based on these requirements.

PROJECT CONTEXT:
{json.dumps(project_context, indent=2)}

REQUIREMENTS ANALYSIS:
{json.dumps(requirements, indent=2)}

Generate test scenarios that cover:

1. **HAPPY PATH SCENARIOS** (Priority: High)
   - Core user journeys working as expected
   - Standard data inputs and outputs
   - Normal system interactions

2. **EDGE CASE SCENARIOS** (Priority: Medium-High)
   - Boundary value testing
   - Unusual but valid user behaviors
   - System limits and constraints

3. **ERROR HANDLING SCENARIOS** (Priority: High)
   - Invalid inputs and error recovery
   - Network failures and timeouts
   - Authentication/authorization failures

4. **INTEGRATION SCENARIOS** (Priority: Medium)
   - API interactions and data flow
   - Third-party service integrations
   - Cross-browser/device compatibility

5. **PERFORMANCE SCENARIOS** (Priority: Medium)
   - Load testing scenarios
   - Response time validation
   - Resource usage monitoring

6. **SECURITY SCENARIOS** (Priority: High)
   - Input validation and sanitization
   - Authentication bypass attempts
   - Data exposure prevention

For each scenario, provide:
- **ID**: Unique identifier
- **Name**: Descriptive title
- **Description**: Detailed explanation
- **Priority**: high|medium|low
- **Category**: functional|technical|performance|security
- **Prerequisites**: What needs to be set up
- **Steps**: Detailed test steps
- **Expected Outcome**: What should happen
- **Validation Points**: How to verify success
- **Risk Level**: impact if this scenario fails
- **Automation Potential**: how easily this can be automated

Format as a JSON array of scenario objects that both TINAA and IDE can process and refine.
"""

    @staticmethod
    def scenario_refinement_prompt(
        current_scenarios: list[dict[str, Any]],
        feedback: dict[str, str],
        additional_requirements: str | None = None,
    ) -> str:
        """Generate prompt for refining test scenarios based on feedback"""
        return f"""
As TINAA's adaptive test planner, refine these test scenarios based on collaborative feedback from the IDE and user input.

CURRENT SCENARIOS:
{json.dumps(current_scenarios, indent=2)}

IDE/USER FEEDBACK:
{json.dumps(feedback, indent=2)}

ADDITIONAL REQUIREMENTS:
{additional_requirements or "None provided"}

Apply the feedback to improve the scenarios by:

1. **ADDRESSING SPECIFIC FEEDBACK**
   - Modify scenarios based on IDE suggestions
   - Incorporate user corrections and preferences
   - Resolve any identified gaps or conflicts

2. **ENHANCING SCENARIO QUALITY**
   - Add missing test cases identified in feedback
   - Improve scenario descriptions for clarity
   - Adjust priorities based on business needs

3. **OPTIMIZING FOR AUTOMATION**
   - Identify scenarios best suited for automation
   - Suggest Page Object Model patterns
   - Recommend data-driven testing approaches

4. **COLLABORATIVE IMPROVEMENTS**
   - Suggest areas where IDE can assist with implementation
   - Identify opportunities for real-time code generation
   - Recommend collaborative debugging strategies

5. **VALIDATION ENHANCEMENTS**
   - Strengthen expected outcomes and assertions
   - Add comprehensive validation checkpoints
   - Include performance and accessibility checks

Return the refined scenarios in the same JSON format, ensuring:
- All feedback has been addressed
- Scenarios are more detailed and actionable
- Automation potential is clearly identified
- Collaborative opportunities are highlighted

Include a summary of changes made and rationale for major modifications.
"""

    @staticmethod
    def playbook_generation_prompt(
        project_context: dict[str, Any],
        requirements: dict[str, Any],
        scenarios: list[dict[str, Any]],
        conversation_history: list[dict[str, Any]],
    ) -> str:
        """Generate prompt for creating comprehensive test playbook"""
        return f"""
As TINAA's master test orchestrator, create a comprehensive, executable test playbook from our collaborative design session.

PROJECT CONTEXT:
{json.dumps(project_context, indent=2)}

REQUIREMENTS:
{json.dumps(requirements, indent=2)}

TEST SCENARIOS:
{json.dumps(scenarios, indent=2)}

COLLABORATION HISTORY:
{json.dumps(conversation_history, indent=2)}

Create a detailed playbook that includes:

1. **PLAYBOOK METADATA**
   - Name and description
   - Creation timestamp and version
   - Estimated execution time
   - Complexity assessment
   - Prerequisites and dependencies

2. **EXECUTION PHASES**
   - **Setup Phase**: Environment preparation, data setup, authentication
   - **Core Testing Phase**: Main test execution with scenarios
   - **Validation Phase**: Result verification and reporting
   - **Cleanup Phase**: Environment reset and resource cleanup

3. **DETAILED STEPS**
   For each step provide:
   - **ID**: Unique step identifier
   - **Action**: Specific action type (navigate, click, fill, verify, etc.)
   - **Parameters**: Detailed parameters for the action
   - **Description**: Human-readable description
   - **Expected Outcome**: What should happen
   - **Error Handling**: How to handle failures
   - **Retry Logic**: When and how to retry
   - **Validation Points**: Success criteria

4. **AUTOMATION GUIDANCE**
   - Page Object Model recommendations
   - Selector strategies and best practices
   - Data management approaches
   - Parallel execution opportunities

5. **COLLABORATION HOOKS**
   - Points where IDE assistance is valuable
   - Real-time feedback opportunities
   - Code generation suggestions
   - Dynamic adaptation possibilities

6. **MONITORING AND REPORTING**
   - Progress tracking mechanisms
   - Result collection strategies
   - Performance metrics to capture
   - Error reporting and debugging aids

7. **MAINTENANCE GUIDANCE**
   - Update procedures for changing requirements
   - Refactoring recommendations
   - Performance optimization opportunities
   - Continuous improvement suggestions

Format the playbook as a comprehensive JSON structure that can be:
- Executed by TINAA's automation engine
- Enhanced by IDE code generation
- Monitored in real-time
- Adapted based on execution results
- Maintained and evolved over time

Ensure the playbook reflects the collaborative design process and enables continued collaboration during execution.
"""

    @staticmethod
    def problem_solving_prompt(
        problem_description: str,
        context: dict[str, Any],
        session_context: dict[str, Any] | None = None,
    ) -> str:
        """Generate prompt for internal problem solving during design/testing"""
        return f"""
As TINAA's internal problem-solving AI, analyze and solve this testing challenge with deep technical expertise.

PROBLEM DESCRIPTION:
{problem_description}

CURRENT CONTEXT:
{json.dumps(context, indent=2)}

SESSION CONTEXT:
{json.dumps(session_context or {}, indent=2)}

Provide a comprehensive solution analysis:

1. **PROBLEM ANALYSIS**
   - Root cause identification
   - Contributing factors
   - Impact assessment
   - Complexity evaluation

2. **SOLUTION APPROACH**
   - Primary recommended solution
   - Alternative approaches
   - Implementation strategy
   - Resource requirements

3. **TECHNICAL IMPLEMENTATION**
   - Specific code patterns or configurations
   - Tool recommendations
   - Integration considerations
   - Performance implications

4. **TESTING STRATEGY**
   - How to validate the solution
   - Test cases to verify fix
   - Regression testing needs
   - Monitoring requirements

5. **RISK MITIGATION**
   - Potential risks and side effects
   - Mitigation strategies
   - Rollback procedures
   - Contingency plans

6. **COLLABORATIVE OPPORTUNITIES**
   - How IDE can assist with implementation
   - Real-time validation possibilities
   - Shared debugging strategies
   - Knowledge sharing opportunities

7. **FUTURE PREVENTION**
   - How to prevent similar issues
   - Process improvements
   - Tool enhancements
   - Best practice updates

Provide actionable, specific guidance that can be implemented immediately while considering the broader context of the testing project and collaborative workflow.
"""

    @staticmethod
    def code_review_prompt(
        code: str, review_focus: str, project_context: dict[str, Any]
    ) -> str:
        """Generate prompt for collaborative code review"""
        return f"""
As TINAA's code quality expert, perform a comprehensive {review_focus} review of this Playwright test code in the context of our collaborative testing project.

CODE TO REVIEW:
```typescript
{code}
```

PROJECT CONTEXT:
{json.dumps(project_context, indent=2)}

REVIEW FOCUS: {review_focus}

Conduct a thorough analysis covering:

1. **CODE QUALITY ASSESSMENT**
   - Readability and maintainability score (1-10)
   - Adherence to Playwright best practices
   - Code organization and structure
   - Naming conventions and clarity

2. **{review_focus.upper()} SPECIFIC ANALYSIS**
   {CollaborativePrompts._get_review_focus_details(review_focus)}

3. **FUNCTIONAL CORRECTNESS**
   - Logic accuracy and completeness
   - Proper error handling
   - Edge case coverage
   - Assertion quality and coverage

4. **AUTOMATION EXCELLENCE**
   - Selector strategy effectiveness
   - Wait strategy optimization
   - Page Object Model implementation
   - Test data management

5. **COLLABORATION OPPORTUNITIES**
   - Areas where IDE assistance would improve code
   - Real-time refactoring suggestions
   - Automated improvement possibilities
   - Pair programming recommendations

6. **IMPROVEMENT RECOMMENDATIONS**
   - Specific code changes needed
   - Refactoring opportunities
   - Performance optimizations
   - Maintainability enhancements

7. **FUTURE CONSIDERATIONS**
   - Scalability implications
   - Evolution and adaptation needs
   - Integration with broader test suite
   - Continuous improvement opportunities

Provide specific, actionable feedback that enhances both the immediate code quality and the long-term collaborative development process.
"""

    @staticmethod
    def _get_review_focus_details(focus: str) -> str:
        """Get specific details for different review focus areas"""
        focus_details = {
            "performance": """
   - Execution speed and efficiency
   - Resource usage optimization
   - Selector performance analysis
   - Wait strategy effectiveness
   - Parallel execution opportunities
   - Memory usage and cleanup
            """,
            "security": """
   - Credential and sensitive data handling
   - Input validation and sanitization
   - Authentication/authorization testing
   - Data exposure prevention
   - Secure communication practices
   - Privacy and compliance considerations
            """,
            "accessibility": """
   - WCAG compliance validation
   - Screen reader compatibility
   - Keyboard navigation testing
   - Color contrast verification
   - ARIA attribute validation
   - Assistive technology support
            """,
            "maintainability": """
   - Code organization and modularity
   - Documentation and comments
   - Test independence and isolation
   - Reusability and DRY principles
   - Version control considerations
   - Team collaboration support
            """,
        }
        return focus_details.get(focus, "General code quality analysis")

    @staticmethod
    def session_summary_prompt(
        session_data: dict[str, Any], outcomes: list[str]
    ) -> str:
        """Generate prompt for summarizing collaborative sessions"""
        return f"""
As TINAA's session analyst, create a comprehensive summary of this collaborative test design session.

SESSION DATA:
{json.dumps(session_data, indent=2)}

KEY OUTCOMES:
{json.dumps(outcomes, indent=2)}

Generate a detailed session summary including:

1. **SESSION OVERVIEW**
   - Duration and timeline
   - Participants and their contributions
   - Major milestones achieved
   - Collaboration effectiveness

2. **REQUIREMENTS EVOLUTION**
   - Initial requirements vs final requirements
   - Key insights discovered during session
   - Assumption validations and corrections
   - Scope clarifications and adjustments

3. **DESIGN DECISIONS**
   - Major design choices made
   - Rationale for each decision
   - Alternative approaches considered
   - Trade-offs and compromises

4. **COLLABORATION HIGHLIGHTS**
   - Most effective collaborative moments
   - IDE assistance utilization
   - Real-time problem solving instances
   - Knowledge sharing achievements

5. **DELIVERABLES CREATED**
   - Test scenarios developed
   - Playbooks generated
   - Code artifacts produced
   - Documentation created

6. **LESSONS LEARNED**
   - Process improvements identified
   - Tool enhancement opportunities
   - Best practices discovered
   - Anti-patterns to avoid

7. **NEXT STEPS**
   - Immediate action items
   - Implementation priorities
   - Monitoring and validation needs
   - Future collaboration opportunities

8. **RECOMMENDATIONS**
   - Process improvements for future sessions
   - Tool configurations and optimizations
   - Team workflow enhancements
   - Continuous improvement suggestions

Create a summary that serves as both a record of accomplishments and a guide for future collaborative testing endeavors.
"""


class PromptTemplates:
    """Template management for collaborative prompts"""

    @staticmethod
    def get_template(template_name: str, **kwargs) -> str:
        """Get a formatted prompt template"""
        templates = {
            "discovery_analysis": CollaborativePrompts.discovery_analysis_prompt,
            "scenario_generation": CollaborativePrompts.scenario_generation_prompt,
            "scenario_refinement": CollaborativePrompts.scenario_refinement_prompt,
            "playbook_generation": CollaborativePrompts.playbook_generation_prompt,
            "problem_solving": CollaborativePrompts.problem_solving_prompt,
            "code_review": CollaborativePrompts.code_review_prompt,
            "session_summary": CollaborativePrompts.session_summary_prompt,
        }

        template_func = templates.get(template_name)
        if not template_func:
            raise ValueError(f"Unknown template: {template_name}")

        return template_func(**kwargs)

    @staticmethod
    def customize_prompt(base_prompt: str, customizations: dict[str, str]) -> str:
        """Apply customizations to a base prompt"""
        customized = base_prompt

        for placeholder, value in customizations.items():
            customized = customized.replace(f"{{{placeholder}}}", value)

        return customized

    @staticmethod
    def validate_prompt_inputs(template_name: str, inputs: dict[str, Any]) -> list[str]:
        """Validate that all required inputs are provided for a template"""
        required_inputs = {
            "discovery_analysis": ["project_context", "answers"],
            "scenario_generation": ["requirements", "project_context"],
            "scenario_refinement": ["current_scenarios", "feedback"],
            "playbook_generation": [
                "project_context",
                "requirements",
                "scenarios",
                "conversation_history",
            ],
            "problem_solving": ["problem_description", "context"],
            "code_review": ["code", "review_focus", "project_context"],
            "session_summary": ["session_data", "outcomes"],
        }

        required = required_inputs.get(template_name, [])
        missing = [req for req in required if req not in inputs]

        return missing
