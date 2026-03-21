"""Shared FastMCP instance.

Kept in a separate module so that ``tools.py`` and ``resources.py`` can both
import ``mcp`` without creating circular dependencies with ``server.py``.
"""

from fastmcp import FastMCP

mcp = FastMCP(
    "TINAA MSP — Testing Intelligence Network Automation Assistant",
    instructions=(
        "Managed Service Platform for continuous quality management. "
        "Register products, run tests, monitor performance, and manage application quality."
    ),
)
