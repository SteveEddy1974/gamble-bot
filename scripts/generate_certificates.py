#!/usr/bin/env python3
"""
Generate SSL certificates for Betfair Exchange API authentication.

This script uses Python's cryptography library to generate self-signed
certificates without requiring OpenSSL to be installed.
"""
import os
import sys
from datetime import datetime, timedelta


def generate_certificates():
    """Generate self-signed SSL certificates for Betfair API."""
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
    except ImportError:
        print("Error: cryptography library not installed")
        print()
        print("Install it with:")
        print("  pip install cryptography")
        sys.exit(1)
    
    print("=" * 70)
    print("GENERATING SSL CERTIFICATES")
    print("=" * 70)
    print()
    
    # Generate private key
    print("1. Generating 2048-bit RSA private key...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    print("   ✓ Private key generated")
    
    # Create certificate subject
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "GB"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "England"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "London"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Betfair Client"),
        x509.NameAttribute(NameOID.COMMON_NAME, "betfair.client"),
    ])
    
    # Generate certificate
    print("2. Creating self-signed certificate...")
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.utcnow()
    ).not_valid_after(
        datetime.utcnow() + timedelta(days=365)
    ).add_extension(
        x509.BasicConstraints(ca=False, path_length=None),
        critical=True,
    ).sign(private_key, hashes.SHA256())
    print("   ✓ Certificate created (valid for 365 days)")
    
    # Write private key to file
    print("3. Writing files...")
    with open("client-2048.key", "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    print("   ✓ client-2048.key")
    
    # Write certificate to file
    with open("client-2048.crt", "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    print("   ✓ client-2048.crt")
    
    # Create PEM file (combined)
    with open("client-2048.pem", "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    print("   ✓ client-2048.pem")
    
    print()
    print("=" * 70)
    print("SUCCESS!")
    print("=" * 70)
    print()
    print("Certificate files created:")
    print(f"  - {os.path.abspath('client-2048.key')} (private key - KEEP SECURE!)")
    print(f"  - {os.path.abspath('client-2048.crt')} (certificate - upload to Betfair)")
    print(f"  - {os.path.abspath('client-2048.pem')} (combined format)")
    print()
    print("=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print()
    print("1. Upload client-2048.crt to your Betfair account:")
    print("   https://myaccount.betfair.com/accountdetails/mysecurity?showAPI=1")
    print()
    print("   - Scroll to 'Automated Betting Program Access'")
    print("   - Click 'Edit'")
    print("   - Upload client-2048.crt")
    print("   - Click 'Save'")
    print()
    print("2. Get your Application Key:")
    print("   https://www.betfair.com → Account → API Access")
    print()
    print("3. Run the authentication setup:")
    print("   python scripts/setup_exchange_auth.py")
    print()
    print("=" * 70)
    print()
    print("SECURITY NOTES:")
    print("- Keep client-2048.key secure (anyone with this can use your certificate)")
    print("- Don't commit these files to version control")
    print("- Back them up safely")
    print("- Certificate expires in 365 days (re-generate then)")
    print()


if __name__ == '__main__':
    if os.path.exists('client-2048.key') or os.path.exists('client-2048.crt'):
        print()
        print("Warning: Certificate files already exist!")
        print()
        response = input("Overwrite existing certificates? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("Cancelled.")
            sys.exit(0)
        print()
    
    generate_certificates()
