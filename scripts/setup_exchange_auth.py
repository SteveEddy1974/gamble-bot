#!/usr/bin/env python3
"""
Betfair Exchange API - Certificate-based Authentication Setup

This script helps you authenticate with Betfair Exchange API using SSL certificates
as documented in the official Betfair API documentation.

Usage: python scripts/setup_exchange_auth.py
"""
import sys
import os
import subprocess
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import load_config
import requests


def check_certificates():
    """Check if SSL certificates exist."""
    cert_files = {
        'crt': 'client-2048.crt',
        'key': 'client-2048.key',
        'pem': 'client-2048.pem'
    }
    
    found = {}
    for file_type, filename in cert_files.items():
        if os.path.exists(filename):
            found[file_type] = filename
    
    return found


def generate_certificates():
    """Guide user through certificate generation."""
    print("=" * 70)
    print("BETFAIR CERTIFICATE GENERATION GUIDE")
    print("=" * 70)
    print()
    print("To use Betfair Exchange API for automated trading, you need SSL certificates.")
    print()
    print("STEP 1: Generate Self-Signed Certificate")
    print("-" * 70)
    print()
    print("You need OpenSSL installed. Download from: https://www.openssl.org/")
    print()
    print("Run these commands:")
    print()
    print("1. Generate private key:")
    print("   openssl genrsa -out client-2048.key 2048")
    print()
    print("2. Create certificate signing request:")
    print("   openssl req -new -key client-2048.key -out client-2048.csr")
    print()
    print("3. Self-sign the certificate:")
    print("   openssl x509 -req -days 365 -in client-2048.csr -signkey client-2048.key -out client-2048.crt")
    print()
    print("4. (Windows only) Create PEM file:")
    print("   type client-2048.crt client-2048.key > client-2048.pem")
    print()
    print("STEP 2: Upload Certificate to Betfair")
    print("-" * 70)
    print()
    print("1. Go to: https://myaccount.betfair.com/accountdetails/mysecurity?showAPI=1")
    print("2. Scroll to 'Automated Betting Program Access'")
    print("3. Click 'Edit'")
    print("4. Upload client-2048.crt")
    print("5. Save")
    print()
    print("STEP 3: Get Application Key")
    print("-" * 70)
    print()
    print("1. Go to: https://www.betfair.com")
    print("2. Login → Account → API Access")
    print("3. Click 'Get an Application Key'")
    print("4. Copy the key")
    print()
    
    input("Press Enter when you have completed the above steps...")


def test_certificate_login(cert_path, key_path, app_key, username, password):
    """Test certificate-based login."""
    print()
    print("=" * 70)
    print("TESTING CERTIFICATE LOGIN")
    print("=" * 70)
    print()
    
    try:
        from urllib.parse import quote
        
        # URL encode username and password
        username_encoded = quote(username)
        password_encoded = quote(password)
        
        payload = f"username={username_encoded}&password={password_encoded}"
        
        headers = {
            'X-Application': app_key,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        print(f"Certificate: {cert_path}")
        print(f"Key: {key_path}")
        print(f"App Key: {app_key}")
        print(f"Username: {username}")
        print()
        print("Attempting login...")
        
        resp = requests.post(
            'https://identitysso-cert.betfair.com/api/certlogin',
            data=payload,
            cert=(cert_path, key_path),
            headers=headers,
            timeout=10
        )
        
        print(f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            try:
                data = resp.json()
                
                if data.get('loginStatus') == 'SUCCESS':
                    session_token = data.get('sessionToken')
                    print()
                    print("✓ SUCCESS!")
                    print()
                    print("=" * 70)
                    print("SESSION TOKEN")
                    print("=" * 70)
                    print()
                    print(f"Token: {session_token}")
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
                    print("=" * 70)
                    print()
                    print("IMPORTANT NOTES:")
                    print("- Token expires after 4-8 hours")
                    print("- Re-run this script when it expires")
                    print("- Keep token secure")
                    print()
                    
                    return session_token
                else:
                    print(f"✗ Login failed: {data.get('loginStatus')}")
                    print()
                    print("Common error codes:")
                    print("- INVALID_USERNAME_OR_PASSWORD: Check credentials")
                    print("- CERT_AUTH_REQUIRED: Certificate not uploaded to Betfair")
                    print("- ACCOUNT_NOW_LOCKED: Too many failed attempts")
                    print()
                    print(f"Full response: {data}")
                    
            except Exception as e:
                print(f"✗ Error parsing response: {e}")
                print(f"Response text: {resp.text}")
        else:
            print(f"✗ HTTP Error: {resp.status_code}")
            print(f"Response: {resp.text[:500]}")
    
    except FileNotFoundError as e:
        print(f"✗ Certificate file not found: {e}")
        print()
        print("Make sure you have:")
        print(f"- {cert_path}")
        print(f"- {key_path}")
        print()
        print("Run the certificate generation steps first.")
    
    except Exception as e:
        print(f"✗ Error: {e}")
    
    return None


def main():
    """Main setup flow."""
    print()
    print("=" * 70)
    print("BETFAIR EXCHANGE API - AUTHENTICATION SETUP")
    print("=" * 70)
    print()
    
    config = load_config()
    username = config['credentials']['username']
    password = config['credentials']['password']
    
    # Check for existing certificates
    certs = check_certificates()
    
    if certs:
        print("✓ Found certificate files:")
        for file_type, path in certs.items():
            print(f"  - {path}")
        print()
    else:
        print("✗ No certificate files found in current directory")
        print()
        generate_certificates()
        
        # Check again
        certs = check_certificates()
        if not certs:
            print("✗ Certificates still not found. Please generate them manually.")
            print()
            print("Once you have client-2048.crt and client-2048.key, re-run this script.")
            return
    
    # Get app key
    app_key = config.get('bot', {}).get('exchange_app_key', '')
    
    if not app_key or app_key == "":
        print("⚠️  No Exchange API app key found in config.yaml")
        print()
        app_key = input("Enter your Exchange API app key: ").strip()
        
        if not app_key:
            print("✗ App key required. Get one from:")
            print("   https://www.betfair.com → Account → API Access")
            return
    
    # Test login
    cert_path = certs.get('crt', 'client-2048.crt')
    key_path = certs.get('key', 'client-2048.key')
    
    session_token = test_certificate_login(cert_path, key_path, app_key, username, password)
    
    if session_token:
        print()
        print("=" * 70)
        print("NEXT STEPS")
        print("=" * 70)
        print()
        print("1. Update config.yaml with the settings shown above")
        print()
        print("2. Test the connection:")
        print("   python -c \"from api_client import ExchangeAPIClient; \\")
        print("              client = ExchangeAPIClient('YOUR_APP_KEY', 'YOUR_TOKEN'); \\")
        print("              print(client.list_market_book(['1.123']))\"")
        print()
        print("3. Run the bot with Exchange API:")
        print("   python main.py")
        print()


if __name__ == '__main__':
    main()
