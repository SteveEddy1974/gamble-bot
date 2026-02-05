# Betfair Exchange Games API - Setup Guide (Official)

**Based on:** Betfair Exchange Games API v1.142 User Guide  
**Date:** February 3, 2026

---

## Key Facts from Official Documentation

### 1. The Exchange Games API is FREE to use
- No special application or approval required
- No API keys needed
- Simple HTTP header authentication

### 2. Base URL
```
https://api.games.betfair.com/rest/v1
```

### 3. Authentication (Required Headers)

The API uses **three HTTP headers** for authentication:

#### Header 1: `gamexAPIPassword`
- **Value:** Your Betfair password (plaintext, **NOT MD5 hashed**)
- **Format:** `gamexAPIPassword: your_password`

#### Header 2: `gamexAPIAgent`
- **Value:** Your application identifier with version
- **Format:** `gamexAPIAgent: email@domain.com.AppName.Version`
- **Example:** `gamexAPIAgent: steve@aquacreations.ltd.BaccaratBot.1.0`

#### Header 3: `gamexAPIAgentInstance`
- **Value:** 32-character MD5 hash unique to each installation
- **How to generate:**
  1. Take current timestamp: `2026-02-03T14:30:00.000Z`
  2. Append a 5-digit random number: `2026-02-03T14:30:00.000Z12345`
  3. Append your gamexAPIAgent ID: `2026-02-03T14:30:00.000Z12345steve@aquacreations.ltd.BaccaratBot.1.0`
  4. Take MD5 hash of the result
- **Example:** `gamexAPIAgentInstance: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`

### 4. Username in URL
- Add `?username=your@email.com` to all API request URLs
- **Example:** `https://api.games.betfair.com/rest/v1/channels/12345/snapshot?username=steve@aquacreations.ltd`

---

## Important Corrections from Previous Attempts

### ❌ WRONG (what we had before):
```python
# DO NOT USE MD5 for password!
md5 = hashlib.md5(password.encode()).hexdigest()
headers = {
    'gamexAPIPassword': md5,  # ❌ WRONG
    'gamexAPIAgent': username,  # ❌ WRONG
    'gamexAPIAgentInstance': md5  # ❌ WRONG
}
```

### ✅ CORRECT (per official guide):
```python
# Use plaintext password
headers = {
    'gamexAPIPassword': password,  # ✅ Plaintext
    'gamexAPIAgent': 'steve@aquacreations.ltd.BaccaratBot.1.0',  # ✅ App ID
    'gamexAPIAgentInstance': generate_instance_id()  # ✅ Unique MD5 per install
}
```

---

## Common Endpoints

### List all available channels (games)
```
GET https://api.games.betfair.com/rest/v1/channels?username=your@email.com
```

### Get current game snapshot for a specific channel
```
GET https://api.games.betfair.com/rest/v1/channels/{channelId}/snapshot?username=your@email.com
```

### For Baccarat Side Bets (what we need):
```
GET https://api.games.betfair.com/rest/v1/channels/{channelId}/snapshot?username=your@email.com&selectionsType=SideBets
```

### Place a bet
```
POST https://api.games.betfair.com/rest/v1/bet/order?username=your@email.com
Content-Type: application/xml
```

---

## Setup Steps

### Step 1: Get a Betfair Account
- Register at www.betfair.com if you don't have an account
- Log in to games.betfair.com
- Accept the Terms and Conditions for Exchange Games
- **Log out** (important - must log out before using API)

### Step 2: Find Your Channel ID
- Visit https://games.betfair.com/exchange-baccarat/turbo/
- Open DevTools (F12) → Network tab
- Reload page (F5)
- Look for: `channels/XXXXX/snapshot`
- Copy the channel ID (XXXXX)

### Step 3: Set Environment Variables (Recommended)
```powershell
$env:BETFAIR_USERNAME = "your@email.com"
$env:BETFAIR_PASSWORD = "your_password"
```

### Step 4: Test Connection
```bash
python scripts/test_connection.py
```

### Step 5: Dry-Run with Real API
```bash
python scripts/dry_run_real_api.py 50 --channel XXXXX --balance 50
```

---

## Polling Guidelines

- **Recommended frequency:** Every 3 seconds
- **Do not poll faster than:** 1 second
- Games have betting windows of 30-60 seconds per round
- Use `bettingWindowPercentageComplete` to optimize timing

---

## Error Handling

### 401 Unauthorized
- Check username/password are correct
- Ensure you've accepted Terms & Conditions on the website
- Ensure you've logged OUT of the website

### 404 Not Found
- Check channel ID is valid
- Channel may be inactive

### Rate Limiting
- Respect the 3-second polling guideline
- API may block excessive requests

---

## Security Notes

- **Never commit passwords to version control**
- Use environment variables for credentials
- The API expects **plaintext** passwords in headers (HTTPS encrypts the connection)
- Generate a new `gamexAPIAgentInstance` ID for each installation

---

## References

- **Official PDF Guide:** Betfair-Exchange-Games-API-User-Guide.pdf (in workspace)
- **Base URL:** https://api.games.betfair.com/rest/v1
- **Games Website:** https://games.betfair.com
- **Main Betfair Site:** https://www.betfair.com

---

## Next Steps

Once you have your channel ID and credentials set up:

1. Run dry-run tests to validate connectivity
2. Monitor for 100+ iterations to confirm bet opportunities
3. Compare with simulation results
4. Enable live trading when ready (set `simulate: false` in config.yaml)

**Remember:** Start with small stakes (£2-5 per bet) for the first live session!
