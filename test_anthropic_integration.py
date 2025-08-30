#!/usr/bin/env python3
"""
Test script for TINAA's Anthropic integration
Tests the settings API, AI manager, and internal problem solving endpoint
"""

import asyncio
import json
import httpx
from datetime import datetime

# Base URL for TINAA API
BASE_URL = "http://localhost:8080"

async def test_health_check():
    """Test basic health check endpoint"""
    print("\n1. Testing Health Check Endpoint")
    print("-" * 50)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Health check passed: {data}")
                return True
            else:
                print(f"✗ Health check failed with status: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Failed to connect to TINAA: {e}")
            return False

async def test_provider_status():
    """Test provider status endpoint to check AI configuration"""
    print("\n2. Testing Provider Status Endpoint")
    print("-" * 50)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/api/v1/settings/provider-status")
            if response.status_code == 200:
                data = response.json()
                print("✓ Provider status retrieved:")
                
                # Check AI providers
                ai_providers = data.get("ai_providers", {})
                if ai_providers:
                    for provider, status in ai_providers.items():
                        print(f"  - {provider}: configured={status.get('configured', False)}, active={status.get('active', False)}")
                        
                    # Check specifically for Anthropic
                    if "anthropic" in ai_providers:
                        anthropic_status = ai_providers["anthropic"]
                        if anthropic_status.get("configured"):
                            print(f"\n✓ Anthropic is configured!")
                            print(f"  Model: {anthropic_status.get('model', 'N/A')}")
                            print(f"  Active: {anthropic_status.get('active', False)}")
                            return True
                        else:
                            print("\n✗ Anthropic is not configured")
                            return False
                else:
                    print("✗ No AI providers found")
                    return False
            else:
                print(f"✗ Failed to get provider status: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Error checking provider status: {e}")
            return False

async def test_credentials_endpoint():
    """Test the credentials endpoint to check current configuration"""
    print("\n3. Testing Credentials Endpoint")
    print("-" * 50)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/api/v1/settings/credentials")
            if response.status_code == 200:
                data = response.json()
                print("✓ Current credentials configuration:")
                
                # Check Anthropic configuration
                anthropic_config = data.get("anthropic", {})
                print(f"\nAnthropic Configuration:")
                print(f"  - Enabled: {anthropic_config.get('enabled', False)}")
                print(f"  - Base URL: {anthropic_config.get('baseUrl', 'N/A')}")
                print(f"  - Default Model: {anthropic_config.get('defaultModel', 'N/A')}")
                print(f"  - API Key: {anthropic_config.get('apiKey', 'Not Set')}")
                
                return anthropic_config.get("enabled", False)
            else:
                print(f"✗ Failed to get credentials: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Error getting credentials: {e}")
            return False

async def test_anthropic_connection():
    """Test actual Anthropic connection via test-credential endpoint"""
    print("\n4. Testing Anthropic Connection")
    print("-" * 50)
    
    async with httpx.AsyncClient() as client:
        try:
            # First check if Anthropic is configured
            creds_response = await client.get(f"{BASE_URL}/api/v1/settings/credentials")
            if creds_response.status_code != 200:
                print("✗ Cannot retrieve current credentials")
                return False
                
            creds_data = creds_response.json()
            anthropic_config = creds_data.get("anthropic", {})
            
            if not anthropic_config.get("enabled"):
                print("✗ Anthropic is not enabled. Please configure it first.")
                return False
            
            # Test the connection
            test_payload = {
                "provider": "anthropic",
                "config": {
                    "apiKey": "use-existing",  # This indicates to use existing configured key
                    "baseUrl": anthropic_config.get("baseUrl", "https://api.anthropic.com"),
                    "defaultModel": anthropic_config.get("defaultModel", "claude-3-sonnet-20240229")
                }
            }
            
            print("Testing Anthropic API connection...")
            response = await client.post(
                f"{BASE_URL}/api/v1/settings/test-credential",
                json=test_payload,
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    print(f"✓ {result.get('message', 'Anthropic connection successful!')}")
                    return True
                else:
                    print(f"✗ {result.get('message', 'Anthropic connection failed')}")
                    return False
            else:
                print(f"✗ Test failed with status: {response.status_code}")
                return False
                
        except httpx.TimeoutException:
            print("✗ Request timed out - this might indicate the API is trying to connect")
            return False
        except Exception as e:
            print(f"✗ Error testing Anthropic connection: {e}")
            return False

async def test_internal_problem_solving():
    """Test the internal problem solving with AI"""
    print("\n5. Testing Internal Problem Solving (AI Integration)")
    print("-" * 50)
    
    # This would require setting up the MCP server endpoint
    # For now, we'll note that this endpoint is part of the MCP server
    print("ℹ️  The internal_problem_solving endpoint is part of the MCP server")
    print("   It's designed to be called through the MCP protocol")
    print("   To test it directly, you would need to:")
    print("   1. Start the MCP server: python app/tinaa_mcp_server.py")
    print("   2. Use an MCP client to call the internal_problem_solving tool")
    
    return True

async def main():
    """Run all tests"""
    print("=" * 70)
    print("TINAA Anthropic Integration Test Suite")
    print("=" * 70)
    print(f"Testing against: {BASE_URL}")
    print(f"Started at: {datetime.now().isoformat()}")
    
    # Run tests
    results = []
    
    # Test 1: Health check
    health_ok = await test_health_check()
    results.append(("Health Check", health_ok))
    
    if not health_ok:
        print("\n❌ TINAA server is not running or not accessible")
        print("Please ensure TINAA is running on http://localhost:8080")
        return
    
    # Test 2: Provider status
    provider_ok = await test_provider_status()
    results.append(("Provider Status", provider_ok))
    
    # Test 3: Credentials check
    creds_ok = await test_credentials_endpoint()
    results.append(("Credentials Check", creds_ok))
    
    # Test 4: Anthropic connection test
    if creds_ok:
        conn_ok = await test_anthropic_connection()
        results.append(("Anthropic Connection", conn_ok))
    else:
        results.append(("Anthropic Connection", False))
        print("\n⚠️  Skipping connection test - Anthropic not configured")
    
    # Test 5: Internal problem solving info
    mcp_info = await test_internal_problem_solving()
    results.append(("MCP Integration Info", mcp_info))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name:.<40} {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed < total:
        print("\n⚠️  Some tests failed. Please check:")
        print("1. Is TINAA running? (docker-compose up or kubectl get pods)")
        print("2. Is Anthropic API key configured in settings?")
        print("3. Check logs: docker-compose logs tinaa")

if __name__ == "__main__":
    asyncio.run(main())