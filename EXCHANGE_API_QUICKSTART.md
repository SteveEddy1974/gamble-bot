# Betfair Exchange API - Quick Start Guide

This guide follows the official Betfair API documentation for non-interactive (bot) authentication.

## Overview

The bot is already configured to use the **Betfair Exchange API** (the standard API for automated betting). The `ExchangeAPIClient` class in `api_client.py` implements the correct pattern - we just need to set up authentication.

## Authentication Requirements

For automated trading, Betfair requires **SSL certificate-based authentication**. This is a 3-step process:

1. Generate SSL certificates
2. Upload certificate to your Betfair account
3. Get session token using certificates

## Step 1: Generate SSL Certificates

You need **OpenSSL** installed. Download from: https://www.openssl.org/

### Windows Commands:

```powershell
# 1. Generate 2048-bit RSA private key
openssl genrsa -out client-2048.key 2048

# 2. Create certificate signing request (CSR)
openssl req -new -key client-2048.key -out client-2048.csr

# 3. Self-sign the certificate (valid for 1 year)
openssl x509 -req -days 365 -in client-2048.csr -signkey client-2048.key -out client-2048.crt

# 4. (Optional) Create PEM format for some tools
type client-2048.crt client-2048.key > client-2048.pem
```

When prompted during CSR creation, you can use any values for the fields (Country, Organization, etc.) - they don't matter for self-signed certificates.

### What you'll have:

- `client-2048.key` - Private key (KEEP SECURE!)
- `client-2048.csr` - Certificate signing request (used for generation only)
- `client-2048.crt` - Public certificate (upload this to Betfair)
- `client-2048.pem` - Combined format (optional)

## Step 2: Upload Certificate to Betfair

1. Go to: https://myaccount.betfair.com/accountdetails/mysecurity?showAPI=1
2. Scroll down to **"Automated Betting Program Access"**
3. Click **"Edit"**
4. Click **"Browse"** and select `client-2048.crt`
5. Click **"Upload Certificate"**
6. Click **"Save"**

**Important:** Wait a few minutes after uploading for the certificate to become active.

## Step 3: Get Application Key

You need an **Application Key** from Betfair:

1. Go to: https://www.betfair.com
2. Login → **Account** → **API Access**
3. Click **"Get an Application Key"**
4. Copy the key (format: `XXXXXXXXXXXXXXXX`)

## Step 4: Get Session Token

Run the helper script:

```powershell
python scripts/setup_exchange_auth.py
```

This will:
- Check for certificate files
- Guide you through the setup if needed
- Test the certificate-based login
- Provide a session token
- Show you exactly what to add to `config.yaml`

### Manual Token Request (if needed):

```python
import requests

app_key = "YOUR_APP_KEY"
username = "YOUR_USERNAME"
password = "YOUR_PASSWORD"

resp = requests.post(
    'https://identitysso-cert.betfair.com/api/certlogin',
    data={'username': username, 'password': password},
    cert=('client-2048.crt', 'client-2048.key'),
    headers={
        'X-Application': app_key,
        'Content-Type': 'application/x-www-form-urlencoded'
    }
)

data = resp.json()
if data['loginStatus'] == 'SUCCESS':
    session_token = data['sessionToken']
    print(f"Token: {session_token}")
else:
    print(f"Error: {data['loginStatus']}")
```

## Step 5: Configure the Bot

Add to `config.yaml`:

```yaml
bot:
  use_exchange_api: true
  exchange_app_key: "YOUR_APP_KEY_HERE"
  exchange_session_token: "YOUR_SESSION_TOKEN_HERE"
```

## Step 6: Test the Connection

Quick test:

```python
from api_client import ExchangeAPIClient

client = ExchangeAPIClient('YOUR_APP_KEY', 'YOUR_TOKEN')

# Test: List all event types
result = client.json_rpc('listEventTypes', {})
print(result)
```

Or run the dry-run test:

```powershell
python scripts/dry_run_real_api.py
```

## Important Notes

### Session Token Expiry
- Tokens are valid for **4-8 hours**
- When expired, re-run `setup_exchange_auth.py` to get a new token
- The bot will show authentication errors when token expires

### Certificate Security
- Keep `client-2048.key` secure - anyone with this file can use your certificate
- Don't commit certificates to version control
- Back them up safely

### API Limits
- Betfair has rate limits on API calls
- The bot implements retry logic and request delays
- Monitor for "THROTTLED" errors in production

### Common Errors

**401 Unauthorized:**
- Certificate not uploaded to Betfair account
- Incorrect app key
- Expired session token

**CERT_AUTH_REQUIRED:**
- Certificate not active yet (wait a few minutes after upload)
- Wrong certificate uploaded
- Certificate expired (regenerate after 1 year)

**INVALID_USERNAME_OR_PASSWORD:**
- Check credentials in config.yaml
- Account may be locked (too many failed attempts)

**THROTTLED:**
- Too many API requests
- Wait and retry (bot handles this automatically)

## What's Different from Games API?

| Feature | Games API | Exchange API |
|---------|-----------|--------------|
| Authentication | MD5 hash (special access) | SSL certificates (standard) |
| Access | Requires approval | Available to all verified accounts |
| Markets | Betfair Games (Baccarat, Hi-Lo, etc.) | Sports & Exchange markets |
| Status | 401 errors (needs approval) | ✓ Working with certificates |
| Client Class | `APIClient` | `ExchangeAPIClient` |

The bot currently uses `ExchangeAPIClient` which is the correct choice for standard automated betting.

## Next Steps After Setup

1. **Test in Dry-Run Mode:**
   ```powershell
   python scripts/dry_run_real_api.py
   ```
   - Connects to real API
   - Evaluates real market data
   - No real bets placed
   - Safe testing

2. **Monitor Test Results:**
   - Check API connectivity
   - Verify market data format
   - Confirm opportunity detection
   - Validate sizing logic

3. **Gradual Production Deployment:**
   - Start with minimum stake (£2)
   - Monitor 100 bets before increasing
   - Track actual vs. simulated performance
   - Implement kill-switch (max daily loss)

## Support Resources

- **Official Docs:** https://docs.developer.betfair.com/display/1smk3cen4v3lu3yomq5qye0ni/API+Overview
- **Non-Interactive Login:** https://docs.developer.betfair.com/display/1smk3cen4v3lu3yomq5qye0ni/Non-Interactive+%28bot%29+login
- **Betfair API Support:** https://developer.betfair.com/support/

## File Summary

The bot has these authentication-related files:

- `api_client.py` - Contains both `APIClient` (Games) and `ExchangeAPIClient` (standard)
- `scripts/setup_exchange_auth.py` - Interactive setup helper
- `scripts/dry_run_real_api.py` - Test bot with real API
- `config.yaml` - Store app key and session token here

## Quick Command Reference

```powershell
# Generate certificates
openssl genrsa -out client-2048.key 2048
openssl req -new -key client-2048.key -out client-2048.csr
openssl x509 -req -days 365 -in client-2048.csr -signkey client-2048.key -out client-2048.crt

# Get session token
python scripts/setup_exchange_auth.py

# Test connection
python scripts/dry_run_real_api.py

# Run bot (after successful dry-run)
python main.py
```

---

**You're ready to proceed once you have:**
✓ Generated SSL certificates
✓ Uploaded certificate to Betfair
✓ Obtained Application Key
✓ Got session token via setup script
✓ Updated config.yaml with keys/token
