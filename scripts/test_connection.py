#!/usr/bin/env python3
"""Test Betfair API connection and authentication.

This script validates that your credentials are correct and the API is accessible.

Usage: python scripts/test_connection.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import getpass

from main import load_config
from api_client import APIClient
import requests


def test_connection():
    """Test basic API connectivity and authentication."""
    config = load_config()

    creds = config.get('credentials', {}) if isinstance(config, dict) else {}
    username = os.getenv('BETFAIR_USERNAME') or (creds.get('username') if isinstance(creds, dict) else None)
    password = os.getenv('BETFAIR_PASSWORD') or (creds.get('password') if isinstance(creds, dict) else None)
    if not username:
        username = input('Betfair username/email: ').strip()
    if not password:
        password = getpass.getpass('Betfair password (input hidden): ').strip()
    config['credentials'] = {'username': username, 'password': password}
    
    print("=== Betfair API Connection Test ===")
    print()
    print(f"Username: {config['credentials']['username']}")
    print(f"API Base URL: {APIClient.BASE_URL}")
    print()
    
    # Test 1: Basic connectivity
    print("Test 1: Basic HTTP connectivity...")
    try:
        resp = requests.get("https://api.games.betfair.com", timeout=10)
        print(f"✓ Can reach Betfair API (status: {resp.status_code})")
    except Exception as e:
        print(f"✗ Cannot reach Betfair API: {e}")
        return
    
    print()
    
    # Test 2: Authentication headers
    print("Test 2: Authentication setup...")
    try:
        api_client = APIClient(config['credentials'])
        print(f"✓ API client initialized")
        print(f"  Headers: {list(api_client.session.headers.keys())}")
    except Exception as e:
        print(f"✗ Failed to initialize API client: {e}")
        return
    
    print()
    
    # Test 3: Try a simple API call
    print("Test 3: Test API endpoint...")
    print("Note: This will likely fail without a valid channel ID, but we can check the error type")
    
    test_endpoints = [
        "/rest/v1/channels",
        "/rest/v1/game/baccarat",
        "/rest/v1/user/balance"
    ]
    
    for endpoint in test_endpoints:
        try:
            url = f"https://api.games.betfair.com{endpoint}"
            resp = api_client.session.get(url, timeout=5)
            print(f"✓ {endpoint}: {resp.status_code}")
            if resp.status_code == 200:
                print(f"  Success! Content length: {len(resp.content)} bytes")
            elif resp.status_code == 401:
                print(f"  Authentication failed - check credentials")
            elif resp.status_code == 404:
                print(f"  Endpoint not found - may need different path")
            else:
                print(f"  Response: {resp.text[:200]}")
        except Exception as e:
            print(f"✗ {endpoint}: {e}")
    
    print()
    print("=" * 50)
    print("NEXT STEPS:")
    print()
    print("If you see 401 errors:")
    print("  - Verify BETFAIR_USERNAME/BETFAIR_PASSWORD (or config.yaml credentials)")
    print("  - Check if your account has Games API access enabled")
    print("  - Review Betfair Games API documentation for auth requirements")
    print()
    print("If you see 404 errors:")
    print("  - The endpoint paths may be different")
    print("  - Consult the Betfair Games API documentation")
    print("  - You may need to use a different authentication method")
    print()
    print("To proceed with real API testing, you'll need:")
    print("  1. Valid credentials with Games API access")
    print("  2. A specific channel ID for a Baccarat table")
    print("  3. Correct API endpoint URLs")
    print()


if __name__ == '__main__':
    test_connection()
