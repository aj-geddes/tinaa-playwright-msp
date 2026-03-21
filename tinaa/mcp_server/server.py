"""TINAA MCP Server entry point.

Imports the shared FastMCP instance from ``_mcp`` and registers all tools
and resources by importing their side-effect modules.  Provides a runnable
entry point supporting both stdio and HTTP transports.
"""

from fastmcp import Context  # noqa: F401  (re-exported for external use)

import tinaa.mcp_server.resources  # noqa: E402, F401

# Register tools and resources by importing their side-effect modules.
import tinaa.mcp_server.tools  # noqa: E402, F401
from tinaa.mcp_server._mcp import mcp  # noqa: F401  (re-exported)


def main():
    """Entry point for the tinaa MCP server (stdio transport)."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    import sys

    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    mcp.run(transport=transport)
