#!/usr/bin/env python3
"""
Quick test to verify TINAA can access Anthropic API key in pod
"""
import asyncio
import os
import sys

# Add TINAA app directory to path
sys.path.insert(0, "/app")


async def test_anthropic_access():
    """Test if TINAA can access and use Anthropic from pod environment"""

    print("🧪 Quick Anthropic Access Test")
    print("=" * 40)

    try:
        # Import TINAA's secrets manager
        from secrets_manager import SecretsManager

        secrets_mgr = SecretsManager()

        print("\n1️⃣ Checking environment...")
        print(f"   Is Kubernetes: {secrets_mgr.is_kubernetes}")
        print(
            f"   Environment: {secrets_mgr.get_environment_info()['kubernetes_namespace'] or 'local'}"
        )

        # Check for Anthropic API key
        print("\n2️⃣ Looking for Anthropic API key...")
        api_key = await secrets_mgr.get_secret("tinaa-anthropic-secret", "api-key")

        if api_key:
            print(f"   ✅ Found API key: {api_key[:10]}...")

            # Get full Anthropic config
            print("\n3️⃣ Loading Anthropic configuration...")
            config = await secrets_mgr.get_ai_provider_config("anthropic")

            if config.get("api_key"):
                print("   ✅ Configuration loaded successfully")
                print(f"   - Base URL: {config.get('base_url')}")
                print(f"   - Model: {config.get('default_model')}")

                # Try to initialize AI manager
                print("\n4️⃣ Initializing AI Manager...")
                from ai_integration import AIManager

                ai_mgr = AIManager()
                await ai_mgr.initialize_from_secrets()

                if "anthropic" in ai_mgr.providers:
                    print("   ✅ Anthropic provider initialized!")

                    # Make a test call
                    print("\n5️⃣ Testing Anthropic API call...")
                    try:
                        response = await ai_mgr.chat_completion(
                            "Reply with just 'OK' to confirm you're working.",
                            provider="anthropic",
                        )
                        if response and "OK" in response.upper():
                            print("   ✅ Anthropic API call successful!")
                            print(f"   Response: {response}")
                        else:
                            print(f"   ⚠️  Unexpected response: {response}")
                    except Exception as e:
                        print(f"   ❌ API call failed: {e}")
                else:
                    print("   ❌ Anthropic provider not initialized")
                    print(f"   Available providers: {list(ai_mgr.providers.keys())}")
            else:
                print("   ❌ No API key in configuration")
        else:
            print("   ❌ API key not found in secrets")

            # Check alternative locations
            print("\n   🔍 Checking alternative secret names...")
            alt_key = await secrets_mgr.get_secret("anthropic-secret", "api-key")
            if alt_key:
                print(f"   ✅ Found in 'anthropic-secret': {alt_key[:10]}...")

            # Check environment variables
            print("\n   🔍 Checking environment variables...")
            env_vars = [
                "ANTHROPIC_API_KEY",
                "TINAA_ANTHROPIC_SECRET_API_KEY",
                "ANTHROPIC_SECRET_API_KEY",
            ]
            for var in env_vars:
                value = os.environ.get(var)
                if value:
                    print(f"   ✅ Found {var}: {value[:10]}...")
                    break

    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 40)
    print("🏁 Test complete!")


if __name__ == "__main__":
    # Run from inside the pod: kubectl exec -it <pod-name> -- python /app/quick_anthropic_test.py
    asyncio.run(test_anthropic_access())
