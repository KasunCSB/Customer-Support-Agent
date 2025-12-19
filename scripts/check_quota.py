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

def check_embedding_quota():
    """Test embedding API and check rate limit headers."""
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION")
    deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
    
    url = f"{endpoint}/openai/deployments/{deployment}/embeddings?api-version={api_version}"
    headers = {
        "api-key": api_key,
        "Content-Type": "application/json"
    }
    
    # Test with a single short text
    data = {"input": "test"}
    
    print("=" * 60)
    print("AZURE OPENAI QUOTA DIAGNOSTICS")
    print("=" * 60)
    print(f"\nEndpoint: {endpoint}")
    print(f"Deployment: {deployment}")
    print(f"API Version: {api_version}")
    print()
    
    response = requests.post(url, headers=headers, json=data)
    
    print(f"Status Code: {response.status_code}")
    print()
    
    # Check rate limit headers
    print("Rate Limit Headers:")
    rate_limit_headers = {
        "x-ratelimit-limit-requests": "Requests per minute limit",
        "x-ratelimit-limit-tokens": "Tokens per minute limit",
        "x-ratelimit-remaining-requests": "Remaining requests",
        "x-ratelimit-remaining-tokens": "Remaining tokens",
        "x-ratelimit-reset-requests": "Reset time for requests",
        "x-ratelimit-reset-tokens": "Reset time for tokens",
        "retry-after": "Seconds to wait before retry",
    }
    
    found_headers = False
    for header, description in rate_limit_headers.items():
        value = response.headers.get(header)
        if value:
            print(f"  {description}: {value}")
            found_headers = True
    
    if not found_headers:
        print("  (No rate limit headers found in response)")
    
    print()
    
    if response.status_code == 200:
        print("✅ API call successful!")
        print("\nYour current quota appears to be working.")
        print("If you're still seeing rate limits during ingestion,")
        print("you may need to request a quota increase.")
    elif response.status_code == 429:
        print("❌ RATE LIMITED (429)")
        print("\nYou have exceeded your quota. See instructions below.")
        
        # Try to get more info
        try:
            error_data = response.json()
            if "error" in error_data:
                print(f"\nError message: {error_data['error'].get('message', 'N/A')}")
        except:
            pass
    elif response.status_code == 401:
        print("❌ AUTHENTICATION FAILED (401)")
        print("\nCheck your API key is correct.")
    elif response.status_code == 404:
        print("❌ DEPLOYMENT NOT FOUND (404)")
        print(f"\nDeployment '{deployment}' does not exist.")
        print("Check your deployment name in Azure Portal.")
    else:
        print(f"❌ UNEXPECTED ERROR ({response.status_code})")
        print(response.text[:500])
    
    print()
    print("=" * 60)
    print("HOW TO INCREASE YOUR AZURE OPENAI QUOTA")
    print("=" * 60)
    print("""
STEP 1: Go to Azure Portal
   https://portal.azure.com

STEP 2: Navigate to your Azure OpenAI resource
   - Search for "Azure OpenAI" in the top search bar
   - Click on your resource (likely in swedencentral region)

STEP 3: Check Current Quota
   - Click "Quotas" in the left sidebar
   - Find "text-embedding-3-large" row
   - Note your current "Tokens per Minute Rate Limit"

STEP 4: Request Quota Increase
   Option A - Use the Portal:
   - Click on the deployment row
   - Click "Request quota increase"
   - Request at least 120,000 TPM for embedding-model
   
   Option B - Edit Deployment:
   - Go to "Deployments" in left sidebar
   - Click on "embedding-model"
   - Increase "Tokens per Minute Rate Limit" slider
   - Click "Save"

STEP 5: Verify
   - Wait 5-10 minutes for changes to propagate
   - Run this script again to verify

RECOMMENDED QUOTA SETTINGS:
   - Development: 60,000 TPM (tokens per minute)
   - Production: 240,000+ TPM
   - High Volume: Consider PTU (Provisioned Throughput)

ALTERNATIVE: Use a different region
   Some regions have more available capacity:
   - East US, East US 2
   - West US, West US 2
   - North Central US
   - UK South
""")

if __name__ == "__main__":
    check_embedding_quota()
