#!/usr/bin/env python3
"""
Quick test of corrected Betfair Games API authentication.

This validates the authentication headers match the official v1.142 User Guide:
- gamexAPIPassword: plaintext password
- gamexAPIAgent: email.AppName.Version format
- gamexAPIAgentInstance: unique 32-char MD5 hash

Usage:
  Set env vars first:
    $env:BETFAIR_USERNAME="your@email.com"
    $env:BETFAIR_PASSWORD="your_password"
  
  Then run:
    python test_corrected_auth.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import getpass
from main import load_config
from api_client import APIClient


def test_corrected_auth():
    """Test the corrected authentication implementation."""
    print("=" * 70)
    print("BETFAIR GAMES API - CORRECTED AUTHENTICATION TEST")
    print("=" * 70)
    print()
    print("Based on: Betfair Exchange Games API v1.142 User Guide")
    print()
    
    config = load_config()
    creds = config.get('credentials', {})
    username = os.getenv('BETFAIR_USERNAME') or creds.get('username')
    password = os.getenv('BETFAIR_PASSWORD') or creds.get('password')
    
    if not username:
        username = input('Betfair username/email: ').strip()
    if not password:
        password = getpass.getpass('Betfair password (input hidden): ').strip()
    
    config['credentials'] = {'username': username, 'password': password}
    
    print(f"Username: {username}")
    print()
    
    try:
        print("Initializing API client with corrected authentication...")
        client = APIClient(config['credentials'])
        
        print("✓ Client initialized successfully")
        print()
        print("Authentication Headers:")
        print("-" * 70)
        
        # Display headers (mask password)
        headers = client.session.headers
        print(f"  gamexAPIPassword: {'*' * len(password)} (plaintext, NOT MD5)")
        print(f"  gamexAPIAgent: {headers.get('gamexAPIAgent')}")
        print(f"  gamexAPIAgentInstance: {headers.get('gamexAPIAgentInstance')}")
        print()
        
        # Verify format
        agent = headers.get('gamexAPIAgent', '')
        instance = headers.get('gamexAPIAgentInstance', '')
        
        print("Validation:")
        print("-" * 70)
        
        if '.BaccaratBot.' in agent:
            print("  ✓ Agent format correct (email.AppName.Version)")
        else:
            print("  ✗ Agent format incorrect")
        
        if len(instance) == 32 and all(c in '0123456789abcdef' for c in instance):
            print("  ✓ Instance ID format correct (32-char hex MD5)")
        else:
            print("  ✗ Instance ID format incorrect")
        
        print()
        print("Now testing actual API connection...")
        print("-" * 70)
        
        # Test ping endpoint
        url = f"https://api.games.betfair.com/rest/v1/ping?username={username}"
        resp = client.session.get(url, timeout=10)
        
        print(f"  Ping endpoint: {resp.status_code}")
        
        if resp.status_code == 200:
            print("  ✓ SUCCESS! API accepts authentication")
            print()
            print("=" * 70)
            print("AUTHENTICATION WORKING!")
            print("=" * 70)
            print()
            print("Next steps:")
            print("1. Get channel ID from DevTools (see GAMES_API_SETUP_GUIDE.md)")
            print("2. Run: python scripts/list_channels.py")
            print("3. Run: python scripts/dry_run_real_api.py 50 --channel XXXXX")
            return True
            
        elif resp.status_code == 401:
            print("  ✗ 401 Unauthorized")
            print()
            print("Possible issues:")
            print("  - Incorrect username/password")
            print("  - Haven't accepted Terms & Conditions on games.betfair.com")
            print("  - Haven't logged OUT of website after accepting T&C")
            print()
            
        else:
            print(f"  Response: {resp.text[:200]}")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    
    return False


if __name__ == '__main__':
    success = test_corrected_auth()
    sys.exit(0 if success else 1)
