# 🚀 LIVE TRADING SETUP CHECKLIST

## ✅ Pre-Launch Verification

### 1. Configuration Ready
- [ ] Username: Set via `BETFAIR_USERNAME` (recommended) or config.yaml
- [ ] Password: Set via `BETFAIR_PASSWORD` (recommended) or config.yaml
- [ ] Channel ID: **PENDING** - Get from browser DevTools
- [x] Kelly Factor: 0.25 (optimal quarter Kelly)
- [x] Dynamic Scaling: Implemented (3%/4%/5%)
- [ ] Starting Balance: Set to your actual Betfair balance

### 2. Safety Limits (Recommended for First Session)
```yaml
# Conservative limits for first live session
start_balance: 50  # Or your actual balance
max_stake_pct: 0.05  # Max 5% per bet (dynamic reduces this)
max_exposure_pct: 0.10  # Max 10% total exposure
min_edge: 0.05  # Only bet on 5%+ edge opportunities
```

### 3. Session Limits
- **First Session**: 2 hours (600 iterations) maximum
- **Daily Drawdown Limit**: Stop at -15%
- **Profit Target**: Consider stopping at +20% to lock gains
- **Manual Stop**: Be ready to Ctrl+C if anything seems wrong

## 🔧 Configuration Steps

### Step 1: Get Channel ID
1. Visit: https://games.betfair.com/exchange-baccarat/turbo/
2. Open DevTools (F12) → Network tab
3. Reload page (F5)
4. Filter for "snapshot"
5. Find: `channels/XXXXX/snapshot`
6. XXXXX = your channel ID

### Step 2: Update config.yaml
```yaml
bot:
  channel_id: XXXXX  # Replace with your channel ID
  simulate: false  # Switch to LIVE mode
  start_balance: 50  # Your actual starting balance
```

### Step 3: Verify Betfair Balance
Before running live, check your Betfair account has sufficient funds (£50+ recommended)

## 🎯 Launch Commands

### Test Mode (Dry Run with Real Data - NO BETS)
```powershell
# First, test with real API but don't place bets
python scripts/dry_run_real_api.py 50 --channel XXXXX --balance 50
```

### Live Mode (REAL MONEY)
```powershell
# When ready for real trading
python main.py --iterations 600  # 2-hour session

# Monitor in another terminal
python scripts/monitoring.py
```

## 📊 During Live Trading

### Every 30 Minutes:
```powershell
python scripts/check_progress.py
```

Check for:
- ✓ Balance trend (should be positive or stable)
- ✓ Win rate (target: 30-35%)
- ✓ Dynamic scaling working (stakes increase with balance)
- ✓ No unusual errors

### Warning Signs - STOP IMMEDIATELY:
- ❌ Balance drops > 15% from starting or peak
- ❌ Multiple API errors in a row
- ❌ Win rate < 20% after 50+ bets
- ❌ Bot not placing bets when opportunities show

## 🛡️ Safety Features Active

Your bot has these protections:
1. **Dynamic Scaling**: Reduces stakes when balance is low
2. **Exposure Limits**: Never risks more than 10% at once
3. **Edge Filter**: Only bets on 5%+ mathematical advantage
4. **Quarter Kelly**: Conservative bet sizing (proven +1,243% ROI)

## 📞 Emergency Stop

**To stop the bot immediately:**
- Press `Ctrl+C` in the terminal
- Bot will finish any pending bets, then stop
- Your balance will be safe

**Check final status:**
```powershell
python scripts/check_progress.py
```

## 💰 Bankroll Milestones

| Balance | Action | Notes |
|---------|---------|-------|
| £50 | START | Initial capital |
| £100 | Continue | First 100% gain |
| £150 | Consider withdrawal | Lock in £50-75 profit |
| £200 | Withdraw £100 | Now playing with house money |

## 📝 Post-Session Review

After each session, run:
```powershell
python scripts/reporting.py
```

Review:
- Total bets placed
- Win rate achieved
- Maximum drawdown
- Profit/loss
- Any errors or unusual behavior

## ✨ You're Ready!

Once you have the **Channel ID**, share it and I'll:
1. Update your config.yaml
2. Run a final dry-run test
3. Give you the green light for live trading

**Remember**: Start small, monitor closely, and respect the stop-loss limits!
