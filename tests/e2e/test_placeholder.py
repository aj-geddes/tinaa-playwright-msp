"""
Placeholder E2E test to prevent CI failures when no E2E tests exist yet.

This file ensures pytest doesn't fail with "no tests found" error.
E2E tests will be added as the project matures.
"""

import pytest


def test_placeholder():
    """Placeholder test - replace with actual E2E tests"""
    assert True, "This is a placeholder test"


@pytest.mark.skip(reason="E2E tests not yet implemented")
def test_future_e2e():
    """Placeholder for future E2E tests"""
    pass