#!/usr/bin/env python3
"""
AI-Enhanced MCP Handler for TINAA

Adds AI capabilities to existing handlers using the AI integration module.
"""

import json
import logging
from typing import Optional, Any

try:
    from app.ai_integration import AIManager
except ImportError:
    # Use simplified version if full module not available
    try:
        from app.ai_integration_simple import AIManager
    except ImportError:
        # Create a mock AIManager if neither is available
        class AIManager:
            def __init__(self, *args, **kwargs):
                pass


# from secrets_manager import SecretsManager  # Not needed for simplified version

logger = logging.getLogger("tinaa.ai_enhanced_handler")

# Global AI manager instance
ai_manager: Optional[AIManager ] = None


async def get_ai_manager() -> AIManager:
    """Get or initialize the AI manager"""
    global ai_manager

    if ai_manager is None:
        ai_manager = AIManager()
        await ai_manager.initialize_from_secrets()
        logger.info(
            f"AI Manager initialized with providers: {list(ai_manager.providers.keys())}"
        )
        logger.info(f"Active provider: {ai_manager.active_provider}")

    return ai_manager


async def generate_exploratory_insights(
    url: str,
    title: str,
    screenshot_data: Optional[str ] = None,
    focus_area: str = "general",
    page_content: Optional[str ] = None,
) -> dict[str, Any]:
    """
    Generate AI insights for exploratory testing

    Args:
        url: The URL being tested
        title: Page title
        screenshot_data: Base64 encoded screenshot
        focus_area: Area of focus for testing
        page_content: Optional page HTML content

    Returns:
        Dictionary with AI-generated insights
    """
    try:
        ai = await get_ai_manager()

        if not ai.active_provider:
            logger.warning("No AI provider available for insights generation")
            return {"insights": None, "error": "No AI provider configured"}

        # Create a comprehensive prompt for AI analysis
        prompt = f"""As an expert QA engineer, analyze this website and provide comprehensive testing insights.

URL: {url}
Title: {title}
Focus Area: {focus_area}

Please provide:
1. Initial observations about the site's purpose and functionality
2. Potential areas of concern for testing
3. Specific test scenarios to explore
4. Accessibility considerations
5. Performance observations
6. Security considerations
7. Recommendations for comprehensive testing

Format your response as a structured analysis that will help guide exploratory testing."""

        # If we have page content, add it to the analysis
        if page_content:
            # Truncate to avoid token limits
            content_preview = (
                page_content[:2000] if len(page_content) > 2000 else page_content
            )
            prompt += f"\n\nPage content preview:\n{content_preview}"

        # Generate insights using AI
        logger.info(f"Generating exploratory insights using {ai.active_provider}")
        insights = await ai.chat_completion(prompt)

        return {
            "insights": insights,
            "provider": ai.active_provider,
            "focus_area": focus_area,
            "url": url,
        }

    except Exception as e:
        logger.error(f"Error generating exploratory insights: {e}")
        return {"insights": None, "error": str(e)}


async def analyze_form_fields(form_fields: list) -> dict[str, Any]:
    """
    Use AI to analyze form fields and suggest test data

    Args:
        form_fields: List of detected form fields

    Returns:
        AI suggestions for form testing
    """
    try:
        ai = await get_ai_manager()

        if not ai.active_provider:
            return {"suggestions": None, "error": "No AI provider configured"}

        prompt = f"""Analyze these form fields and suggest appropriate test data:

Form fields:
{json.dumps(form_fields, indent=2)}

Please provide:
1. Suggested test values for each field (valid and invalid cases)
2. Edge cases to test
3. Security testing considerations
4. Validation rules that might apply
5. Accessibility requirements for the form

Format as JSON with field names as keys and test suggestions as values."""

        suggestions = await ai.chat_completion(prompt)

        # Try to parse as JSON if possible
        try:
            suggestions_json = json.loads(suggestions)
            return {"suggestions": suggestions_json, "provider": ai.active_provider}
        except:
            return {"suggestions": suggestions, "provider": ai.active_provider}

    except Exception as e:
        logger.error(f"Error analyzing form fields: {e}")
        return {"suggestions": None, "error": str(e)}


async def generate_accessibility_insights(
    accessibility_results: dict[str, Any], url: str
) -> dict[str, Any]:
    """
    Generate AI insights for accessibility testing results

    Args:
        accessibility_results: Results from accessibility scan
        url: The URL tested

    Returns:
        AI-enhanced accessibility analysis
    """
    try:
        ai = await get_ai_manager()

        if not ai.active_provider:
            return {"analysis": None, "error": "No AI provider configured"}

        prompt = f"""As an accessibility expert, analyze these test results and provide recommendations:

URL: {url}
Accessibility scan results:
{json.dumps(accessibility_results, indent=2)}

Please provide:
1. Severity assessment of found issues
2. Prioritized fix recommendations
3. WCAG compliance impact
4. User impact analysis
5. Best practices for improvement
6. Additional manual testing recommendations"""

        analysis = await ai.chat_completion(prompt)

        return {
            "analysis": analysis,
            "provider": ai.active_provider,
            "original_results": accessibility_results,
        }

    except Exception as e:
        logger.error(f"Error generating accessibility insights: {e}")
        return {"analysis": None, "error": str(e)}


async def generate_security_insights(
    security_observations: dict[str, Any], url: str
) -> dict[str, Any]:
    """
    Generate AI insights for security testing

    Args:
        security_observations: Initial security observations
        url: The URL tested

    Returns:
        AI-enhanced security analysis
    """
    try:
        ai = await get_ai_manager()

        if not ai.active_provider:
            return {"analysis": None, "error": "No AI provider configured"}

        prompt = f"""As a security testing expert, analyze these observations and provide comprehensive security insights:

URL: {url}
Initial observations:
{json.dumps(security_observations, indent=2)}

Please provide:
1. Potential security vulnerabilities
2. OWASP Top 10 considerations
3. Authentication/authorization concerns
4. Data protection assessment
5. Recommended security test cases
6. Priority areas for manual security testing"""

        analysis = await ai.chat_completion(prompt)

        return {
            "analysis": analysis,
            "provider": ai.active_provider,
            "observations": security_observations,
        }

    except Exception as e:
        logger.error(f"Error generating security insights: {e}")
        return {"analysis": None, "error": str(e)}


async def generate_test_report_summary(report_data: dict[str, Any]) -> dict[str, Any]:
    """
    Generate an AI-powered executive summary for test reports

    Args:
        report_data: Complete test report data

    Returns:
        AI-generated summary and recommendations
    """
    try:
        ai = await get_ai_manager()

        if not ai.active_provider:
            return {"summary": None, "error": "No AI provider configured"}

        prompt = f"""Create an executive summary for this test report:

Test Report Data:
{json.dumps(report_data, indent=2)}

Please provide:
1. Executive summary (2-3 paragraphs)
2. Key findings and risks
3. Prioritized recommendations
4. Next steps for the team
5. Overall quality assessment

Make it concise but comprehensive for stakeholders."""

        summary = await ai.chat_completion(prompt)

        return {
            "summary": summary,
            "provider": ai.active_provider,
            "generated_at": report_data.get("timestamp", ""),
        }

    except Exception as e:
        logger.error(f"Error generating test report summary: {e}")
        return {"summary": None, "error": str(e)}
