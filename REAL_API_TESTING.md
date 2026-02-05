# Real API Dry-Run Testing Guide

This guide explains how to test the bot with real Betfair API data **without placing actual bets**.

## Prerequisites

1. Betfair credentials provided via environment variables (recommended):

  - `BETFAIR_USERNAME`
  - `BETFAIR_PASSWORD`

  (Alternatively you can place credentials under `credentials:` in `config.yaml`, but avoid committing secrets.)
2. Active internet connection
3. Accept Terms & Conditions on games.betfair.com (then log out)
4. **See [GAMES_API_SETUP_GUIDE.md](GAMES_API_SETUP_GUIDE.md) for complete setup instructions**
This will display all available channels with their IDs, names, and status.

## Step 2: Run Real API Dry-Run

Once you have a channel ID, run the dry-run test:

```bash
# Basic usage (100 iterations)
python scripts/dry_run_real_api.py 100 --channel CHANNEL_ID

# Extended test (500 iterations)
python scripts/dry_run_real_api.py 500 --channel CHANNEL_ID

# Custom balance and exposure
python scripts/dry_run_real_api.py 200 --channel CHANNEL_ID --balance 5000 --exposure 0.15
```

### Arguments

- `iterations`: Number of polling cycles to run (default: 100)
- `--channel`: Channel ID to monitor (required)
- `--balance`: Starting balance for simulation (default: 1000)
- `--exposure`: Max exposure as decimal (default: 0.1 = 10%)

## Step 3: Analyze Results

The dry-run will show:

- **Opportunities Found**: Total +EV opportunities detected
- **Would Place**: Bets that would have been placed
- **Skipped (Exposure/Balance)**: Bets skipped due to risk limits
- **Total Would Stake**: Sum of all stakes that would have been placed
- **API Errors**: Connection or parsing errors

### Example Output

```
[10/100] Cards: 392, Opportunities: 5, Would Place: 3
[11/100] ✓ WOULD PLACE BET: Pocket Pair In Any Hand
      Edge: +8.32% | Price: 5.250 | True Prob: 0.206
      Stake: £45.23 | Balance: £1000.00 | Exposure: £123.50
```

## What to Look For

### ✅ Good Signs
- Reasonable number of opportunities (5-15 per 100 iterations)
- Edge percentages in expected range (5-20%)
- No excessive API errors
- Prices consistent with fair value

### ⚠️ Warning Signs
- Zero opportunities found (may indicate pricing is too efficient)
- Excessive API errors (connection/auth issues)
- Extremely high edges (>50%) - may indicate data issues
- Shoe never resets (table may be inactive)

## Step 4: Compare with Simulation

Compare real API results with simulated results:

```bash
# Run simulation for comparison
python scripts/dry_run.py 500

# Compare opportunity frequency, edge distribution, and profitability patterns
```

Key differences to investigate:
- **Opportunity Frequency**: Real markets may have fewer +EV opportunities
- **Edge Size**: Real inefficiencies likely smaller than simulated (0.4-1.4x multiplier)
- **Price Movement**: Real prices may change faster or slower than simulation
- **Shoe Behavior**: Real shoe may deal cards differently

## Troubleshooting

### No Channel ID Available
```bash
# Manually specify a channel ID if list_channels.py doesn't work
python scripts/dry_run_real_api.py 100 --channel 12345
```

### Authentication Errors
- Verify credentials in `config.yaml`
- Check Betfair account status and API access
- Review API documentation for authentication requirements

### No Opportunities Found
- Real markets may be efficient (fewer +EV situations)
- Try longer test runs (500+ iterations)
- Verify MIN_EDGE threshold in `engine.py` isn't too aggressive
- Check that shoe is active (cards_remaining changing)

### Connection Timeouts
- Increase poll_interval_seconds in `config.yaml`
- Check network/firewall settings
- Verify Betfair API endpoint URLs in `api_client.py`

## Next Steps

Once real API dry-run shows reasonable results:

1. **✅ Validate profitability patterns** match simulated expectations
2. **✅ Confirm bet sizing** is appropriate for real balance
3. **✅ Test longer periods** (1000+ iterations over multiple hours)
4. **→ Enable real betting** by setting appropriate flags in `config.yaml`

## Safety Notes

- This script **NEVER places real bets** - it's read-only
- Your balance in dry-run is purely simulated
- No money is at risk during this testing phase
- API calls are made but no bet orders are submitted

## Configuration for Live Trading

When ready to enable real betting:

```yaml
# config.yaml
bot:
  simulate: false          # Disable simulation mode
  channel_id: "YOUR_CHANNEL_ID"  # Set discovered channel ID
  start_balance: 1000      # Your actual starting balance
  max_exposure_pct: 0.10   # Conservative exposure limit
```

⚠️ **WARNING**: Only enable real betting after thorough testing and when you're prepared to risk real money.
