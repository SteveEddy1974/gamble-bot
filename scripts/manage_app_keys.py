#!/usr/bin/env python3
"""
Create or retrieve Betfair Application Key using the Accounts API.

This script uses certificate-based authentication to:
1. Get a session token
2. Create a new Application Key (if needed)
3. Retrieve existing Application Keys

Usage: python scripts/manage_app_keys.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import load_config
import requests
import json


def get_session_token(cert_path, key_path, username, password):
    """Get session token using certificate authentication."""
    print("Getting session token...")
    
    try:
        from urllib.parse import quote
        
        username_encoded = quote(username)
        password_encoded = quote(password)
        payload = f"username={username_encoded}&password={password_encoded}"
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        resp = requests.post(
            'https://identitysso-cert.betfair.com/api/certlogin',
            data=payload,
            cert=(cert_path, key_path),
            headers=headers,
            timeout=10
        )
        
        if resp.status_code == 200:
            data = resp.json()
            
            if data.get('loginStatus') == 'SUCCESS':
                session_token = data.get('sessionToken')
                print(f"✓ Session token obtained")
                return session_token
            else:
                print(f"✗ Login failed: {data.get('loginStatus')}")
                return None
        else:
            print(f"✗ HTTP Error: {resp.status_code}")
            print(f"Response: {resp.text[:500]}")
            return None
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return None


def get_developer_app_keys(session_token):
    """Retrieve existing Application Keys."""
    print()
    print("=" * 70)
    print("RETRIEVING EXISTING APPLICATION KEYS")
    print("=" * 70)
    print()
    
    url = "https://api.betfair.com/exchange/account/json-rpc/v1"
    
    headers = {
        'X-Authentication': session_token,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    payload = {
        "jsonrpc": "2.0",
        "method": "AccountAPING/v1.0/getDeveloperAppKeys",
        "params": {},
        "id": 1
    }
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            
            if 'result' in data:
                app_keys = data['result']
                
                if not app_keys:
                    print("No Application Keys found.")
                    print()
                    print("You need to create one using createDeveloperAppKeys")
                    return []
                
                print(f"Found {len(app_keys)} Application Key(s):")
                print()
                
                for i, key_info in enumerate(app_keys, 1):
                    print(f"Key {i}:")
                    print(f"  App Name: {key_info.get('appName', 'N/A')}")
                    print(f"  App Key:  {key_info.get('appKey', 'N/A')}")
                    print(f"  Created:  {key_info.get('createdDate', 'N/A')}")
                    print()
                
                return app_keys
            
            elif 'error' in data:
                error = data['error']
                print(f"✗ API Error: {error.get('message', 'Unknown error')}")
                print(f"  Code: {error.get('code', 'N/A')}")
                if 'data' in error:
                    print(f"  Data: {error['data']}")
                return []
        else:
            print(f"✗ HTTP Error: {resp.status_code}")
            print(f"Response: {resp.text[:500]}")
            return []
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return []


def create_developer_app_key(session_token, app_name="BaccaratBot"):
    """Create a new Application Key."""
    print()
    print("=" * 70)
    print("CREATING NEW APPLICATION KEY")
    print("=" * 70)
    print()
    print(f"App Name: {app_name}")
    print()
    
    url = "https://api.betfair.com/exchange/account/json-rpc/v1"
    
    headers = {
        'X-Authentication': session_token,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    payload = {
        "jsonrpc": "2.0",
        "method": "AccountAPING/v1.0/createDeveloperAppKeys",
        "params": {
            "appName": app_name
        },
        "id": 1
    }
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            
            if 'result' in data:
                result = data['result']
                app_key = result.get('appKey')
                
                print("✓ SUCCESS!")
                print()
                print("=" * 70)
                print("NEW APPLICATION KEY CREATED")
                print("=" * 70)
                print()
                print(f"App Name: {result.get('appName', 'N/A')}")
                print(f"App Key:  {app_key}")
                print()
                print("=" * 70)
                print("ADD TO config.yaml:")
                print("=" * 70)
                print()
                print("bot:")
                print("  use_exchange_api: true")
                print(f"  exchange_app_key: \"{app_key}\"")
                print(f"  exchange_session_token: \"{session_token}\"")
                print()
                
                return app_key
            
            elif 'error' in data:
                error = data['error']
                print(f"✗ API Error: {error.get('message', 'Unknown error')}")
                print(f"  Code: {error.get('code', 'N/A')}")
                
                if error.get('code') == -32099:  # App key already exists
                    print()
                    print("Hint: You may already have an Application Key.")
                    print("      Use 'getDeveloperAppKeys' to retrieve it.")
                
                if 'data' in error:
                    print(f"  Data: {error['data']}")
                
                return None
        else:
            print(f"✗ HTTP Error: {resp.status_code}")
            print(f"Response: {resp.text[:500]}")
            return None
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return None


def main():
    """Main flow."""
    print()
    print("=" * 70)
    print("BETFAIR APPLICATION KEY MANAGEMENT")
    print("=" * 70)
    print()
    
    # Check for certificates
    cert_path = 'client-2048.crt'
    key_path = 'client-2048.key'
    
    if not os.path.exists(cert_path) or not os.path.exists(key_path):
        print(f"✗ Certificate files not found!")
        print()
        print("Required files:")
        print(f"  - {cert_path}")
        print(f"  - {key_path}")
        print()
        print("Run: python scripts/generate_certificates.py")
        print("Then upload the certificate to Betfair.")
        return
    
    print(f"✓ Found certificates: {cert_path}, {key_path}")
    print()
    
    # Load config
    config = load_config()
    username = config['credentials']['username']
    password = config['credentials']['password']
    
    # Get session token
    session_token = get_session_token(cert_path, key_path, username, password)
    
    if not session_token:
        print()
        print("=" * 70)
        print("TROUBLESHOOTING")
        print("=" * 70)
        print()
        print("Certificate authentication failed. Make sure you have:")
        print()
        print("1. Uploaded client-2048.crt to your Betfair account:")
        print("   https://myaccount.betfair.com/accountdetails/mysecurity?showAPI=1")
        print()
        print("2. Waited a few minutes for the certificate to become active")
        print()
        print("3. Used the correct username and password in config.yaml")
        return
    
    # First, try to retrieve existing keys
    existing_keys = get_developer_app_keys(session_token)
    
    if existing_keys:
        print()
        print("=" * 70)
        print("RECOMMENDED ACTION")
        print("=" * 70)
        print()
        print("Use one of the existing Application Keys shown above.")
        print()
        print("Add to config.yaml:")
        print()
        print("bot:")
        print("  use_exchange_api: true")
        print(f"  exchange_app_key: \"{existing_keys[0].get('appKey')}\"")
        print(f"  exchange_session_token: \"{session_token}\"")
        print()
        return
    
    # No existing keys, offer to create one
    print()
    print("No Application Keys found.")
    print()
    response = input("Create a new Application Key? (yes/no): ").strip().lower()
    
    if response in ['yes', 'y']:
        app_name = input("Enter app name (default: BaccaratBot): ").strip()
        if not app_name:
            app_name = "BaccaratBot"
        
        create_developer_app_key(session_token, app_name)
    else:
        print()
        print("You can create an Application Key later via:")
        print("- This script")
        print("- Betfair website: Account → API Access")
        print("- Accounts API Demo Tool")


if __name__ == '__main__':
    main()
