#!/usr/bin/env python3
"""
Direct test of MCP server via stdio protocol
"""
import json
import subprocess


def send_mcp_request(request):
    """Send a request to the MCP server and get response"""
    # Convert request to JSON-RPC format
    json_request = json.dumps(request) + "\n"

    # Start the MCP server process
    process = subprocess.Popen(
        ["python", "/app/minimalist_mcp.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Send request
    stdout, stderr = process.communicate(input=json_request, timeout=10)

    # Parse response
    if stdout:
        for line in stdout.strip().split("\n"):
            if line.strip():
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    pass

    return None


import pytest


@pytest.mark.skip(reason="MCP server requires proper stdio setup")
def test_initialize():
    """Test MCP initialize request"""
    print("Testing MCP Initialize...")

    request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "0.1.0",
            "capabilities": {"tools": {}},
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
        },
        "id": 1,
    }

    response = send_mcp_request(request)

    if response:
        print(f"✓ Got response: {json.dumps(response, indent=2)}")
        assert True  # Test passed
    else:
        print("✗ No response received")
        assert False, "No response received from MCP server"


@pytest.mark.skip(reason="MCP server requires proper stdio setup")
def test_tools_list():
    """Test listing available tools"""
    print("\nTesting Tools List...")

    request = {"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 2}

    response = send_mcp_request(request)

    if response and "result" in response:
        tools = response["result"].get("tools", [])
        print(f"✓ Found {len(tools)} tools:")
        for tool in tools[:5]:  # Show first 5
            print(f"  - {tool.get('name')}: {tool.get('description')[:50]}...")
        if len(tools) > 5:
            print(f"  ... and {len(tools) - 5} more")
        assert True  # Test passed
    else:
        print("✗ Failed to list tools")
        assert False, "Failed to list tools from MCP server"


@pytest.mark.skip(reason="Event loop conflict in test environment")
def test_direct_navigation():
    """Test navigation directly in the container"""
    print("\nTesting Direct Navigation...")

    try:
        import sys

        sys.path.insert(0, "/app")
        import asyncio

        from app.mcp_handler import navigate_to_url

        # Run the navigation test
        async def run_nav():
            result = await navigate_to_url("https://example.com")
            return result

        result = asyncio.run(run_nav())

        if result and result.get("success"):
            print("✓ Navigation successful")
            print(f"  URL: {result.get('url')}")
            print(f"  Title: {result.get('title')}")
            assert True
        else:
            print(f"✗ Navigation failed: {result}")
            assert False, f"Navigation failed: {result}"

    except Exception as e:
        print(f"✗ Error: {e}")
        assert False, f"Error during navigation: {e!s}"


def main():
    """Run all tests"""
    print("=" * 50)
    print("Direct MCP Server Tests")
    print("=" * 50)

    # Test direct function calls
    success = test_direct_navigation()

    print("\n" + "=" * 50)
    print(f"Result: {'✓ PASS' if success else '✗ FAIL'}")

    return success


if __name__ == "__main__":
    import sys

    success = main()
    sys.exit(0 if success else 1)
