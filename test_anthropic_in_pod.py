#!/usr/bin/env python3
"""
Test TINAA's Anthropic integration when API key is already in the pod
"""
import asyncio
import httpx
import json

async def test_anthropic_in_pod():
    """Test that TINAA can use Anthropic with existing pod credentials"""
    
    # TINAA's base URL - adjust if needed
    base_url = "http://localhost:8765"
    
    print("🔍 Testing TINAA's Anthropic Integration (API key in pod)...")
    print("-" * 50)
    
    async with httpx.AsyncClient() as client:
        # 1. Check provider status
        print("\n1️⃣ Checking AI Provider Status...")
        try:
            response = await client.get(f"{base_url}/api/v1/settings/provider-status")
            if response.status_code == 200:
                status = response.json()
                anthropic_status = status.get("ai_providers", {}).get("anthropic", {})
                
                if anthropic_status.get("configured"):
                    print("✅ Anthropic is configured!")
                    print(f"   - Active: {anthropic_status.get('active', False)}")
                    print(f"   - Model: {anthropic_status.get('model', 'Not set')}")
                else:
                    print("❌ Anthropic is not configured")
                    print("   The API key might not be properly mounted or named")
            else:
                print(f"❌ Failed to get provider status: {response.status_code}")
        except Exception as e:
            print(f"❌ Error checking provider status: {e}")
        
        # 2. Test the internal problem solving endpoint (uses AI)
        print("\n2️⃣ Testing Internal Problem Solving (uses Anthropic)...")
        try:
            test_payload = {
                "problem_description": "Test problem: How can I improve my Playwright test reliability?",
                "context": {
                    "test_type": "integration test",
                    "issue": "flaky tests"
                }
            }
            
            response = await client.post(
                f"{base_url}/api/v1/internal/problem-solving",
                json=test_payload
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("solution"):
                    print("✅ Anthropic AI responded successfully!")
                    print(f"   Solution preview: {result['solution'][:100]}...")
                else:
                    print("❌ No solution returned from AI")
            else:
                print(f"❌ Problem solving failed: {response.status_code}")
                print(f"   Error: {response.text}")
        except Exception as e:
            print(f"❌ Error testing problem solving: {e}")
        
        # 3. Check current credentials (masked)
        print("\n3️⃣ Checking Current Credentials Configuration...")
        try:
            response = await client.get(f"{base_url}/api/v1/settings/credentials")
            if response.status_code == 200:
                creds = response.json()
                anthropic_config = creds.get("anthropic", {})
                
                print(f"   - Enabled: {anthropic_config.get('enabled', False)}")
                print(f"   - API Key: {anthropic_config.get('apiKey', 'Not set')}")
                print(f"   - Base URL: {anthropic_config.get('baseUrl', 'Not set')}")
                print(f"   - Model: {anthropic_config.get('defaultModel', 'Not set')}")
                
                if anthropic_config.get('apiKey') == '••••••••':
                    print("✅ API key is present (masked for security)")
                elif not anthropic_config.get('apiKey'):
                    print("❌ No API key found")
            else:
                print(f"❌ Failed to get credentials: {response.status_code}")
        except Exception as e:
            print(f"❌ Error checking credentials: {e}")
        
        # 4. Test collaborative session (uses AI)
        print("\n4️⃣ Testing Collaborative Session Creation...")
        try:
            session_payload = {
                "project_name": "Test Project",
                "project_description": "Testing Anthropic integration",
                "target_url": "https://example.com"
            }
            
            response = await client.post(
                f"{base_url}/api/v1/collaborative/start-session",
                json=session_payload
            )
            
            if response.status_code == 200:
                session = response.json()
                if session.get("session_id") and session.get("initial_questions"):
                    print("✅ Collaborative session started successfully!")
                    print(f"   - Session ID: {session['session_id']}")
                    print(f"   - Questions generated: {len(session.get('initial_questions', []))}")
                else:
                    print("❌ Session created but no AI-generated questions")
            else:
                print(f"❌ Failed to start session: {response.status_code}")
        except Exception as e:
            print(f"❌ Error testing collaborative session: {e}")

    print("\n" + "-" * 50)
    print("🏁 Test Complete!")
    print("\nℹ️  If Anthropic is not working, check:")
    print("   1. Is the secret mounted correctly in the pod?")
    print("   2. Is the secret named 'tinaa-anthropic-secret'?")
    print("   3. Does it have the key 'api-key' (with hyphen)?")
    print("   4. Check pod logs: kubectl logs <pod-name>")

async def check_secret_mount():
    """Check if secrets are properly mounted in the pod"""
    import os
    
    print("\n📁 Checking Secret Mount Locations...")
    
    # Common secret mount paths
    secret_paths = [
        "/var/run/secrets/tinaa-anthropic-secret",
        "/etc/secrets/tinaa-anthropic-secret",
        "/secrets/tinaa-anthropic-secret",
        "/var/secrets/tinaa-anthropic-secret"
    ]
    
    for path in secret_paths:
        if os.path.exists(path):
            print(f"✅ Found secret mount at: {path}")
            # List files in the directory
            try:
                files = os.listdir(path)
                print(f"   Files: {files}")
                
                # Check for api-key file
                api_key_path = os.path.join(path, "api-key")
                if os.path.exists(api_key_path):
                    print(f"   ✅ api-key file exists")
                    # Don't print the actual key for security
                    with open(api_key_path, 'r') as f:
                        key_preview = f.read()[:10] + "..."
                        print(f"   Key preview: {key_preview}")
            except Exception as e:
                print(f"   ❌ Error reading directory: {e}")
    
    # Check environment variables
    print("\n🔍 Checking Environment Variables...")
    env_vars = [
        "TINAA_ANTHROPIC_SECRET_API_KEY",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_SECRET_API_KEY",
        "TINAA_API_KEY"
    ]
    
    for var in env_vars:
        value = os.environ.get(var)
        if value:
            print(f"✅ Found {var}: {value[:10]}...")

if __name__ == "__main__":
    print("🚀 TINAA Anthropic Integration Test (Pod Environment)")
    print("=" * 50)
    
    # First check secret mounts
    asyncio.run(check_secret_mount())
    
    # Then test the API
    asyncio.run(test_anthropic_in_pod())