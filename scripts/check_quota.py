#!/usr/bin/env python3
"""
Azure OpenAI Quota Checker & Rate Limit Diagnostics

This script helps diagnose rate limiting issues with your Azure OpenAI deployment.
Run: python scripts/check_quota.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
import requests

load_dotenv()


def check_deployment_quota(deployment_name: str, deployment_type: str, test_data: dict) -> dict:
    """
    Test an Azure OpenAI deployment and check rate limit headers.
    
    Args:
        deployment_name: Name of the deployment to test
        deployment_type: API type ("embeddings" or "chat/completions")
        test_data: JSON payload for the test request
        
    Returns:
        dict with status and quota information
    """
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION")
    
    url = f"{endpoint}/openai/deployments/{deployment_name}/{deployment_type}?api-version={api_version}"
    headers = {
        "api-key": api_key,
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, headers=headers, json=test_data)
    
    # Extract rate limit headers
    quota_info = {
        "status_code": response.status_code,
        "limit_requests": response.headers.get("x-ratelimit-limit-requests"),
        "limit_tokens": response.headers.get("x-ratelimit-limit-tokens"),
        "remaining_requests": response.headers.get("x-ratelimit-remaining-requests"),
        "remaining_tokens": response.headers.get("x-ratelimit-remaining-tokens"),
        "reset_requests": response.headers.get("x-ratelimit-reset-requests"),
        "reset_tokens": response.headers.get("x-ratelimit-reset-tokens"),
        "retry_after": response.headers.get("retry-after"),
    }
    
    # Try to get error message if failed
    if response.status_code != 200:
        try:
            error_data = response.json()
            quota_info["error"] = error_data.get("error", {}).get("message", response.text[:200])
        except Exception:
            quota_info["error"] = response.text[:200]
    
    return quota_info


def print_quota_results(name: str, deployment: str, quota_info: dict):
    """Print formatted quota results for a deployment."""
    print(f"\n{'─' * 50}")
    print(f"📊 {name.upper()}")
    print(f"{'─' * 50}")
    print(f"Deployment: {deployment}")
    print(f"Status: {quota_info['status_code']}")
    
    if quota_info["status_code"] == 200:
        print("✅ API call successful!")
    elif quota_info["status_code"] == 429:
        print("❌ RATE LIMITED (429)")
        if quota_info.get("error"):
            print(f"   Error: {quota_info['error']}")
    elif quota_info["status_code"] == 401:
        print("❌ AUTHENTICATION FAILED (401)")
    elif quota_info["status_code"] == 404:
        print(f"❌ DEPLOYMENT NOT FOUND (404)")
    else:
        print(f"❌ UNEXPECTED ERROR ({quota_info['status_code']})")
        if quota_info.get("error"):
            print(f"   Error: {quota_info['error']}")
    
    # Print rate limit info
    if quota_info["limit_tokens"]:
        print(f"\n📈 Rate Limits:")
        print(f"   Tokens/min limit:     {quota_info['limit_tokens']}")
        print(f"   Tokens/min remaining: {quota_info['remaining_tokens']}")
        print(f"   Requests/min limit:   {quota_info['limit_requests']}")
        print(f"   Requests remaining:   {quota_info['remaining_requests']}")
    else:
        print("\n   (No rate limit headers in response)")


def check_all_quotas():
    """Check quota for both embedding and chat deployments."""
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
    chat_deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
    
    print("=" * 60)
    print("🔍 AZURE OPENAI QUOTA DIAGNOSTICS")
    print("=" * 60)
    print(f"\nEndpoint: {endpoint}")
    print(f"Embedding Deployment: {embedding_deployment}")
    print(f"Chat Deployment: {chat_deployment}")
    
    if not all([endpoint, api_key]):
        print("\n❌ ERROR: Missing AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_API_KEY in .env")
        return
    
    # Initialize quota variables
    embedding_quota: dict | None = None
    chat_quota: dict | None = None
    
    # Check embedding quota
    if embedding_deployment:
        embedding_quota = check_deployment_quota(
            deployment_name=embedding_deployment,
            deployment_type="embeddings",
            test_data={"input": "test"}
        )
        print_quota_results("Embedding Model", embedding_deployment, embedding_quota)
    else:
        print("\n⚠️  No embedding deployment configured (AZURE_OPENAI_EMBEDDING_DEPLOYMENT)")
    
    # Check chat/LLM quota
    if chat_deployment:
        chat_quota = check_deployment_quota(
            deployment_name=chat_deployment,
            deployment_type="chat/completions",
            test_data={
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 5
            }
        )
        print_quota_results("Chat/LLM Model", chat_deployment, chat_quota)
    else:
        print("\n⚠️  No chat deployment configured (AZURE_OPENAI_CHAT_DEPLOYMENT)")
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 SUMMARY")
    print("=" * 60)
    
    if embedding_quota and embedding_quota.get("limit_tokens"):
        tpm = int(embedding_quota["limit_tokens"])
        print(f"\nEmbedding TPM: {tpm:,}")
        if tpm < 10000:
            print("   ⚠️  WARNING: Very low quota. Consider increasing to 60K+ TPM")
        elif tpm < 60000:
            print("   💡 Moderate quota. For faster ingestion, increase to 60K+ TPM")
        else:
            print("   ✅ Good quota for development/production use")
    
    if chat_quota and chat_quota.get("limit_tokens"):
        tpm = int(chat_quota["limit_tokens"])
        print(f"\nChat TPM: {tpm:,}")
        if tpm < 10000:
            print("   ⚠️  WARNING: Very low quota. May cause slow responses")
        else:
            print("   ✅ Adequate quota for chat operations")
    
    print_help()


def print_help():
    """Print instructions for increasing quota."""
    print("\n" + "=" * 60)
    print("📖 HOW TO INCREASE YOUR AZURE OPENAI QUOTA")
    print("=" * 60)
    print("""
OPTION 1: Azure Portal (GUI)
   1. Go to https://portal.azure.com
   2. Search for "Azure OpenAI" → Select your resource
   3. Click "Deployments" in left sidebar
   4. Click on deployment → Adjust "Tokens per Minute" slider
   5. Click "Save"

OPTION 2: Azure CLI (Command Line)
   # For embedding model:
   az cognitiveservices account deployment create \\
     -g <resource-group> -n <resource-name> \\
     --deployment-name embedding-model \\
     --model-name text-embedding-3-large \\
     --model-version "1" --model-format OpenAI \\
     --sku-capacity 60 --sku-name "Standard"
   
   # For chat model:
   az cognitiveservices account deployment create \\
     -g <resource-group> -n <resource-name> \\
     --deployment-name chat-model \\
     --model-name gpt-4o-mini \\
     --model-version "2024-07-18" --model-format OpenAI \\
     --sku-capacity 60 --sku-name "Standard"

RECOMMENDED SETTINGS:
   Development:  60,000 TPM (--sku-capacity 60)
   Production:  240,000 TPM (--sku-capacity 240)
   
NOTE: Changes may take 5-10 minutes to propagate.
""")


if __name__ == "__main__":
    check_all_quotas()
