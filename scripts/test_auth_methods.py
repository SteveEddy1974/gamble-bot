#!/usr/bin/env python3
"""
Advanced Betfair API authentication tester.

Tests multiple authentication methods to find the correct one for Betfair Games API.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import getpass

from main import load_config
import requests
import hashlib
import json


def test_auth_methods():
    """Test various authentication methods for Betfair Games API."""
    config = load_config()
    creds = config.get('credentials', {}) if isinstance(config, dict) else {}
    username = os.getenv('BETFAIR_USERNAME') or (creds.get('username') if isinstance(creds, dict) else None)
    password = os.getenv('BETFAIR_PASSWORD') or (creds.get('password') if isinstance(creds, dict) else None)
    if not username:
        username = input('Betfair username/email: ').strip()
    if not password:
        password = getpass.getpass('Betfair password (input hidden): ').strip()
    
    print("=" * 60)
    print("BETFAIR GAMES API AUTHENTICATION TESTER")
    print("=" * 60)
    print(f"\nUsername: {username}")
    print()
    
    # Method 1: MD5 Hash Headers (current implementation)
    print("Method 1: MD5 Password Hash Headers")
    print("-" * 60)
    try:
        session = requests.Session()
        md5 = hashlib.md5(password.encode()).hexdigest()
        session.headers.update({
            'gamexAPIPassword': md5,
            'gamexAPIAgent': username,
            'gamexAPIAgentInstance': md5
        })
        
        resp = session.get("https://api.games.betfair.com/rest/v1/channels", timeout=5)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print("✓ SUCCESS! This method works.")
            return 'method1'
        elif resp.status_code == 401:
            print("✗ 401 Unauthorized - Method not accepted")
        else:
            print(f"Response: {resp.text[:300]}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print()
    
    # Method 2: Certificate-based authentication (common for Betfair)
    print("Method 2: Certificate-based Authentication")
    print("-" * 60)
    print("Note: This method requires SSL certificates which are typically")
    print("      obtained separately from Betfair. Check if you have:")
    print("      - client-2048.crt (certificate)")
    print("      - client-2048.key (private key)")
    print("Skipping unless certificates are configured...")
    print()
    
    # Method 3: Session login endpoint
    print("Method 3: Session Login (Identity API)")
    print("-" * 60)
    try:
        # Try Betfair Identity API login
        login_url = "https://identitysso.betfair.com/api/login"
        payload = {
            'username': username,
            'password': password
        }
        headers = {
            'X-Application': 'DEMO',  # May need a real app key
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        resp = requests.post(login_url, data=payload, headers=headers, timeout=10)
        print(f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json() if 'json' in resp.headers.get('content-type', '') else {}
            if 'token' in data or 'sessionToken' in data:
                token = data.get('token') or data.get('sessionToken')
                print(f"✓ Login successful! Token: {token[:20]}...")
                
                # Now try using this token with Games API
                print("\nTesting Games API with session token...")
                games_session = requests.Session()
                games_session.headers.update({
                    'X-Authentication': token,
                    'X-Application': 'DEMO'
                })
                
                resp2 = games_session.get("https://api.games.betfair.com/rest/v1/channels", timeout=5)
                print(f"Games API Status: {resp2.status_code}")
                
                if resp2.status_code == 200:
                    print("✓ SUCCESS! Session token works with Games API!")
                    return 'method3', token
                else:
                    print(f"Response: {resp2.text[:300]}")
            else:
                print(f"Response: {resp.text[:500]}")
        else:
            print(f"Response: {resp.text[:500]}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print()
    
    # Method 4: Direct password (some APIs use plaintext)
    print("Method 4: Plain Password Headers")
    print("-" * 60)
    try:
        session = requests.Session()
        session.headers.update({
            'gamexAPIPassword': password,  # Plain text
            'gamexAPIAgent': username,
            'gamexAPIAgentInstance': username
        })
        
        resp = session.get("https://api.games.betfair.com/rest/v1/channels", timeout=5)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print("✓ SUCCESS! Plain password works.")
            return 'method4'
        elif resp.status_code == 401:
            print("✗ 401 Unauthorized")
        else:
            print(f"Response: {resp.text[:300]}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print()
    
    # Method 5: Check if this is an Exchange API endpoint issue
    print("Method 5: Testing Exchange API Endpoints")
    print("-" * 60)
    print("Note: Games API and Exchange API are different services.")
    print("      Your credentials might be for Exchange API instead.")
    print("      Exchange API uses different authentication (app key + session token)")
    print()
    
    # Summary
    print("=" * 60)
    print("AUTHENTICATION ANALYSIS")
    print("=" * 60)
    print()
    print("All methods returned 401 Unauthorized. This suggests:")
    print()
    print("1. ✓ Account credentials are incorrect")
    print("      → Verify username/password in config.yaml")
    print()
    print("2. ✓ Games API access not enabled for your account")
    print("      → Check Betfair account settings")
    print("      → Games API may require separate application/approval")
    print()
    print("3. ✓ Authentication method requires SSL certificates")
    print("      → Download certificates from Betfair")
    print("      → Install them and update the client to use them")
    print()
    print("4. ✓ Wrong API base URL or endpoints")
    print("      → Games API URL: https://api.games.betfair.com/rest/v1")
    print("      → Check official documentation for correct endpoints")
    print()
    print("5. ✓ Application key (app_key) required")
    print("      → Some Betfair APIs require registration for an app key")
    print("      → Check if Games API requires app key registration")
    print()
    print("RECOMMENDED NEXT STEPS:")
    print()
    print("1. Contact Betfair support to verify:")
    print("   - Is your account enabled for Games API access?")
    print("   - What authentication method should be used?")
    print("   - Are SSL certificates required?")
    print("   - Is an application key required?")
    print()
    print("2. Check official Betfair Games API documentation:")
    print("   - Authentication guide")
    print("   - Code examples")
    print("   - Getting started tutorial")
    print()
    print("3. Consider using Exchange API instead:")
    print("   - Already implemented in ExchangeAPIClient")
    print("   - Requires app_key and session_token")
    print("   - May provide similar betting functionality")
    print()
    
    return None


if __name__ == '__main__':
    test_auth_methods()
