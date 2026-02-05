#!/usr/bin/env python3
"""
Get Betfair Exchange API session token.

This script helps you obtain a session token for the Betfair Exchange API
using interactive (non-certificate) login.

Usage: python scripts/get_exchange_token.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import load_config
import requests


def get_exchange_session_token():
    """Interactive login to get Exchange API session token."""
    config = load_config()
    
    print("=" * 70)
    print("BETFAIR EXCHANGE API - SESSION TOKEN GENERATOR")
    print("=" * 70)
    print()
    print("This script will help you get a session token for Betfair Exchange API.")
    print()
    
    # Get credentials
    username = config['credentials']['username']
    password = config['credentials']['password']
    
    # Get app key (either from config or prompt)
    app_key = config.get('bot', {}).get('exchange_app_key', '')
    
    if not app_key or app_key == "":
        print("⚠️  No Exchange API app key found in config.yaml")
        print()
        print("To get an app key:")
        print("1. Visit https://www.betfair.com")
        print("2. Log in to your account")
        print("3. Go to: Account → API Access → Application Keys")
        print("4. Click 'Get an Application Key' (or 'Create App Key')")
        print("5. Copy the generated key")
        print()
        
        app_key = input("Enter your Exchange API app key (or press Enter to use 'DEMO'): ").strip()
        if not app_key:
            app_key = "DEMO"
            print("Using 'DEMO' as app key (may not work for all operations)")
    
    print()
    print(f"Username: {username}")
    print(f"App Key: {app_key}")
    print()
    print("Attempting login...")
    print()
    
    try:
        # Method 1: Interactive (non-certificate) login
        print("Method 1: Interactive Login (no certificates required)")
        print("-" * 70)
        
        resp = requests.post(
            'https://identitysso.betfair.com/api/login',
            data={
                'username': username,
                'password': password
            },
            headers={
                'X-Application': app_key,
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            timeout=10
        )
        
        print(f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            try:
                data = resp.json()
                token = data.get('sessionToken') or data.get('token')
                
                if token:
                    print("✓ SUCCESS!")
                    print()
                    print("=" * 70)
                    print("SESSION TOKEN OBTAINED")
                    print("=" * 70)
                    print()
                    print(f"Token: {token}")
                    print()
                    print("=" * 70)
                    print("ADD TO config.yaml:")
                    print("=" * 70)
                    print()
                    print("bot:")
                    print("  use_exchange_api: true")
                    print(f"  exchange_app_key: \"{app_key}\"")
                    print(f"  exchange_session_token: \"{token}\"")
                    print()
                    print("=" * 70)
                    print()
                    print("⚠️  IMPORTANT NOTES:")
                    print()
                    print("1. This token will expire after some time (typically 4-8 hours)")
                    print("2. You'll need to regenerate it when it expires")
                    print("3. For production use, consider certificate-based auth (longer validity)")
                    print("4. Keep this token secure - it provides full account access")
                    print()
                    
                    return token
                else:
                    print("✗ Login response didn't contain a token")
                    print(f"Response: {data}")
                    
            except Exception as e:
                print(f"✗ Error parsing response: {e}")
                print(f"Response text: {resp.text[:500]}")
        else:
            print(f"✗ Login failed: {resp.status_code}")
            print(f"Response: {resp.text[:500]}")
            print()
            print("Common issues:")
            print("- Incorrect username or password")
            print("- Account locked or suspended")
            print("- Invalid app key")
            print("- Account doesn't have API access enabled")
    
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print()
    print("=" * 70)
    print("TROUBLESHOOTING")
    print("=" * 70)
    print()
    print("If login failed:")
    print()
    print("1. Verify credentials in config.yaml are correct")
    print("2. Check if your Betfair account is active and not suspended")
    print("3. Ensure you have a valid app key (not 'DEMO')")
    print("4. Try logging in to https://www.betfair.com in a browser")
    print("5. Check if 2FA (two-factor auth) is enabled (may block API access)")
    print()
    print("For certificate-based auth (more reliable for production):")
    print()
    print("1. Download SSL certificates from Betfair")
    print("2. Use the certificate login endpoint:")
    print("   https://identitysso-cert.betfair.com/api/certlogin")
    print("3. Pass certificates in the request:")
    print("   cert=('client-2048.crt', 'client-2048.key')")
    print()
    
    return None


if __name__ == '__main__':
    get_exchange_session_token()
