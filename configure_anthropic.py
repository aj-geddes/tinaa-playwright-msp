#!/usr/bin/env python3
"""
Script to configure Anthropic API credentials for TINAA
"""

import asyncio
import getpass
import sys

import httpx

BASE_URL = "http://localhost:8080"


async def configure_anthropic():
    """Configure Anthropic API credentials"""
    print("=" * 70)
    print("TINAA - Configure Anthropic Integration")
    print("=" * 70)

    # Check if TINAA is running
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/health")
            if response.status_code != 200:
                print("❌ TINAA server is not responding")
                return False
        except Exception as e:
            print(f"❌ Cannot connect to TINAA at {BASE_URL}")
            print(f"   Error: {e}")
            print("\nPlease ensure TINAA is running:")
            print("  - Docker: docker-compose up")
            print("  - Kubernetes: kubectl get pods")
            return False

    print("✓ TINAA server is running\n")

    # Get Anthropic API key
    print("Please enter your Anthropic API key")
    print("(Get one at https://console.anthropic.com/)")
    api_key = getpass.getpass("API Key: ")

    if not api_key:
        print("❌ API key cannot be empty")
        return False

    # Optional: custom settings
    use_defaults = input("\nUse default settings? (Y/n): ").lower()

    if use_defaults == "n":
        base_url = (
            input("Base URL (default: https://api.anthropic.com): ")
            or "https://api.anthropic.com"
        )
        model = (
            input("Default model (default: claude-3-sonnet-20240229): ")
            or "claude-3-sonnet-20240229"
        )
    else:
        base_url = "https://api.anthropic.com"
        model = "claude-3-sonnet-20240229"

    # Test the credentials first
    print("\n🔍 Testing Anthropic credentials...")
    async with httpx.AsyncClient() as client:
        test_payload = {
            "provider": "anthropic",
            "config": {"apiKey": api_key, "baseUrl": base_url, "defaultModel": model},
        }

        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/settings/test-credential",
                json=test_payload,
                timeout=30.0,
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    print(f"✓ {result.get('message', 'Credentials valid!')}")
                else:
                    print(f"❌ {result.get('message', 'Invalid credentials')}")
                    return False
            else:
                print(f"❌ Test failed: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Error testing credentials: {e}")
            return False

    # Save the credentials
    print("\n💾 Saving Anthropic configuration...")
    async with httpx.AsyncClient() as client:
        config_payload = {
            "anthropic": {
                "enabled": True,
                "apiKey": api_key,
                "baseUrl": base_url,
                "defaultModel": model,
            }
        }

        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/settings/credentials",
                json=config_payload,
                timeout=30.0,
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✓ {result.get('message', 'Configuration saved!')}")
                print("\n🎉 Anthropic integration configured successfully!")
                return True
            print(f"❌ Failed to save configuration: {response.status_code}")
            return False

        except Exception as e:
            print(f"❌ Error saving configuration: {e}")
            return False


async def check_current_config():
    """Check current Anthropic configuration"""
    print("\n📋 Current Anthropic Configuration:")
    print("-" * 40)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/api/v1/settings/credentials")
            if response.status_code == 200:
                data = response.json()
                anthropic = data.get("anthropic", {})

                print(f"Enabled: {anthropic.get('enabled', False)}")
                print(f"Base URL: {anthropic.get('baseUrl', 'Not set')}")
                print(f"Model: {anthropic.get('defaultModel', 'Not set')}")
                print(
                    f"API Key: {'Configured' if anthropic.get('apiKey') else 'Not set'}"
                )

                return anthropic.get("enabled", False)
        except Exception as e:
            print(f"Error: {e}")
            return False


async def main():
    """Main function"""
    # Check current configuration
    is_configured = await check_current_config()

    if is_configured:
        reconfigure = input(
            "\nAnthropic is already configured. Reconfigure? (y/N): "
        ).lower()
        if reconfigure != "y":
            print("Configuration unchanged.")
            return

    # Configure Anthropic
    success = await configure_anthropic()

    if success:
        print("\n✅ You can now test the integration with:")
        print("   python test_anthropic_integration.py")
    else:
        print("\n❌ Configuration failed. Please check the errors above.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nConfiguration cancelled.")
        sys.exit(0)
