#!/usr/bin/env python3
"""
Test which AI provider TINAA is using
"""
import asyncio
import json

import httpx


async def test_ai_provider():
    base_url = "http://localhost:8765"
    
    # Test a simple exploratory request that should trigger AI usage
    test_payload = {
        "action": "exploratory",
        "parameters": {
            "url": "https://www.anthropic.com",
            "prompt": "Tell me about Anthropic and Claude AI. What makes Claude unique?"
        }
    }
    
    print("🧪 Testing TINAA's AI provider...")
    print("📤 Sending exploratory test request...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{base_url}/test/exploratory",
                json=test_payload
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Check if there are insights (AI-generated content)
                if result.get("result", {}).get("insights"):
                    insights = result["result"]["insights"]
                    print("\n✅ AI-generated insights received!")
                    print(f"📝 Insights preview: {insights[:200]}...")
                    
                    # Check for Claude-specific language patterns
                    if any(word in insights.lower() for word in ["claude", "anthropic", "constitutional ai"]):
                        print("\n🎯 Likely using Anthropic Claude!")
                    else:
                        print("\n🤔 AI provider unclear from response")
                else:
                    print("\n❌ No AI insights in response")
                    print("Response:", json.dumps(result, indent=2)[:500])
            else:
                print(f"\n❌ Request failed: {response.status_code}")
                print(f"Response: {response.text[:200]}")
                
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_ai_provider())