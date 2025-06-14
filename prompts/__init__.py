"""
Prompts package for Tina Tester MCP
"""

from .system_message import SYSTEM_MESSAGE
from .authentication_prompts import (
    AUTHENTICATION_PROMPT, 
    AUTHENTICATION_DISCLAIMER,
    CREDENTIAL_REQUEST
)
from .testing_prompts import (
    EXPLORATORY_TEST_PROMPT,
    ACCESSIBILITY_TEST_PROMPT,
    RESPONSIVE_TEST_PROMPT,
    FORM_TEST_PROMPT,
    SECURITY_TEST_BASIC_PROMPT,
    TEST_REPORT_TEMPLATE
)
