#!/usr/bin/env python3
"""
Diagnostic script to troubleshoot Betfair certificate authentication.
"""
import os
import sys
import requests
import getpass
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import load_config


def _get_credentials():
    config = load_config()
    creds = config.get('credentials', {}) if isinstance(config, dict) else {}
    username = os.getenv('BETFAIR_USERNAME') or (creds.get('username') if isinstance(creds, dict) else None)
    password = os.getenv('BETFAIR_PASSWORD') or (creds.get('password') if isinstance(creds, dict) else None)

    if not username:
        username = input('Betfair username/email: ').strip()
    if not password:
        password = getpass.getpass('Betfair password (input hidden): ').strip()

    return username, password

def check_certificate_files():
    """Check if certificate files exist and are readable."""
    print("=" * 70)
    print("CHECKING CERTIFICATE FILES")
    print("=" * 70)
    print()
    
    files = {
        'Certificate': 'client-2048.crt',
        'Private Key': 'client-2048.key'
    }
    
    all_ok = True
    for name, filename in files.items():
        if os.path.exists(filename):
            size = os.path.getsize(filename)
            print(f"✓ {name}: {filename} ({size} bytes)")
        else:
            print(f"✗ {name}: {filename} NOT FOUND")
            all_ok = False
    
    print()
    return all_ok


def validate_certificate():
    """Validate certificate format and dates."""
    print("=" * 70)
    print("VALIDATING CERTIFICATE")
    print("=" * 70)
    print()
    
    try:
        from cryptography import x509
        from cryptography.hazmat.backends import default_backend
        
        with open('client-2048.crt', 'rb') as f:
            cert = x509.load_pem_x509_certificate(f.read(), default_backend())
        
        print(f"Subject: {cert.subject}")
        print(f"Issuer: {cert.issuer}")
        print(f"Valid from: {cert.not_valid_before_utc}")
        print(f"Valid until: {cert.not_valid_after_utc}")
        
        now = datetime.now(cert.not_valid_before_utc.tzinfo)
        if now < cert.not_valid_before_utc:
            print("⚠️  Certificate not yet valid!")
        elif now > cert.not_valid_after_utc:
            print("✗ Certificate expired!")
        else:
            print("✓ Certificate is currently valid")
        
        print()
        return True
        
    except Exception as e:
        print(f"✗ Error validating certificate: {e}")
        print()
        return False


def test_certificate_endpoint():
    """Test the certificate login endpoint."""
    print("=" * 70)
    print("TESTING CERTIFICATE ENDPOINT")
    print("=" * 70)
    print()
    
    # Test 1: Check if endpoint is reachable
    print("Test 1: Endpoint reachability")
    try:
        resp = requests.get('https://identitysso-cert.betfair.com/', timeout=5)
        print(f"  Status: {resp.status_code}")
        print(f"  ✓ Endpoint is reachable")
    except Exception as e:
        print(f"  ✗ Cannot reach endpoint: {e}")
        return False
    
    print()
    
    # Test 2: Try login with certificate
    print("Test 2: Certificate authentication")
    try:
        username, password = _get_credentials()
        payload = {
            'username': username,
            'password': password
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        resp = requests.post(
            'https://identitysso-cert.betfair.com/api/certlogin',
            data=payload,
            cert=('client-2048.crt', 'client-2048.key'),
            headers=headers,
            timeout=10
        )
        
        print(f"  HTTP Status: {resp.status_code}")
        print(f"  Content-Type: {resp.headers.get('Content-Type', 'N/A')}")
        print()
        
        if resp.status_code == 200:
            try:
                data = resp.json()
                print(f"  Response: {data}")
                
                if data.get('loginStatus') == 'SUCCESS':
                    print()
                    print("  ✓ SUCCESS! Certificate authentication working!")
                    return True
                else:
                    print()
                    print(f"  ✗ Login failed: {data.get('loginStatus')}")
                    print()
                    print("  Common error codes:")
                    print("    - INVALID_USERNAME_OR_PASSWORD: Check credentials")
                    print("    - CERT_AUTH_REQUIRED: Certificate not uploaded/active")
                    print("    - ACCOUNT_NOW_LOCKED: Too many failed attempts")
            except Exception as e:
                print(f"  ✗ Cannot parse JSON response: {e}")
                print(f"  Response text: {resp.text[:200]}")
        
        elif resp.status_code == 400:
            print()
            print("  ✗ 400 Bad Request")
            print()
            print("  This usually means:")
            print("    1. Certificate not uploaded to Betfair account")
            print("    2. Certificate uploaded but not activated yet (wait 5-10 min)")
            print("    3. Certificate uploaded to wrong account")
            print("    4. Request format issue")
            print()
            print("  IMPORTANT: Have you uploaded client-2048.crt to:")
            print("  https://myaccount.betfair.com/accountdetails/mysecurity?showAPI=1")
            print()
            print("  Steps:")
            print("    - Scroll to 'Automated Betting Program Access'")
            print("    - Click 'Edit'")
            print("    - Upload client-2048.crt (NOT .key or .pem)")
            print("    - Click 'Save'")
            print("    - Wait 5-10 minutes")
        
        elif resp.status_code == 401:
            print()
            print("  ✗ 401 Unauthorized")
            print("    - Certificate may be uploaded but credentials are wrong")
        
        else:
            print()
            print(f"  ✗ Unexpected status code: {resp.status_code}")
            print(f"  Response: {resp.text[:200]}")
        
    except requests.exceptions.SSLError as e:
        print(f"  ✗ SSL Error: {e}")
        print()
        print("  This might mean:")
        print("    - Certificate or key file is corrupted")
        print("    - Certificate/key mismatch")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    print()
    return False


def test_interactive_login():
    """Test interactive login (without certificate) for comparison."""
    print("=" * 70)
    print("TESTING INTERACTIVE LOGIN (for comparison)")
    print("=" * 70)
    print()
    
    print("This tests if basic credentials work (without certificates)")
    print()
    
    try:
        username, password = _get_credentials()
        payload = {
            'username': username,
            'password': password
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        resp = requests.post(
            'https://identitysso.betfair.com/api/login',
            json=payload,
            headers=headers,
            timeout=10
        )
        
        print(f"HTTP Status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"Response: {data}")
            
            if data.get('status') == 'SUCCESS':
                print()
                print("✓ Credentials are valid (interactive login works)")
                print()
                print("This means the issue is specifically with certificate authentication.")
            else:
                print()
                print(f"✗ Interactive login failed: {data.get('error', 'Unknown error')}")
        
        else:
            print(f"Response: {resp.text[:200]}")
    
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print()


def main():
    """Run all diagnostics."""
    print()
    print("=" * 70)
    print("BETFAIR CERTIFICATE AUTHENTICATION DIAGNOSTICS")
    print("=" * 70)
    print()
    print(f"Date/Time: {datetime.now()}")
    print()
    
    if not check_certificate_files():
        print("✗ Certificate files missing. Run: python scripts/generate_certificates.py")
        return
    
    if not validate_certificate():
        print("✗ Certificate validation failed.")
        return
    
    cert_ok = test_certificate_endpoint()
    
    if not cert_ok:
        test_interactive_login()
    
    print("=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print()
    
    if cert_ok:
        print("✓ Certificate authentication is working!")
        print()
        print("Run: python scripts/manage_app_keys.py")
    else:
        print("Certificate authentication not working yet.")
        print()
        print("If you just uploaded the certificate:")
        print("  1. Wait 10-15 minutes for Betfair to activate it")
        print("  2. Re-run this diagnostic: python scripts/diagnose_cert.py")
        print()
        print("If you haven't uploaded the certificate yet:")
        print("  1. Go to: https://myaccount.betfair.com/accountdetails/mysecurity?showAPI=1")
        print("  2. Upload client-2048.crt (the .crt file, not .key)")
        print("  3. Wait 10-15 minutes")
        print("  4. Re-run this diagnostic")
        print()
        print("If the certificate was uploaded more than 15 minutes ago:")
        print("  - Contact Betfair support: https://support.developer.betfair.com/")
        print("  - They can verify if your account has API access enabled")
    
    print()


if __name__ == '__main__':
    main()
