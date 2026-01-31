#!/usr/bin/env python3
"""Generate SHA256 hash for operator token and print env var instructions.

Usage: python scripts/generate_operator_token_hash.py <token>
"""
import hashlib
import sys

def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode('utf-8')).hexdigest()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python scripts/generate_operator_token_hash.py <token>')
        sys.exit(1)
    token = sys.argv[1]
    h = sha256_hex(token)
    print('SHA256 hash:')
    print(h)
    print('\nSet environment variable (PowerShell):')
    print(f"$env:BOT_OPERATOR_TOKEN = '{token}'")
    print('Or for persistent (PowerShell):')
    print(f"setx BOT_OPERATOR_TOKEN '{token}'")
    print('\nSet environment variable (bash):')
    print(f"export BOT_OPERATOR_TOKEN='{token}'")