# Baccarat Bot - Operations Runbook

## Table of Contents
1. [Starting the Bot](#starting-the-bot)
2. [Stopping the Bot](#stopping-the-bot)
3. [Monitoring Operations](#monitoring-operations)
4. [Error Handling](#error-handling)
5. [Recovery Procedures](#recovery-procedures)
6. [Daily Maintenance](#daily-maintenance)
7. [Troubleshooting](#troubleshooting)

---

## Starting the Bot

### Pre-Flight Checklist
- [ ] Verify Betfair account balance is sufficient (minimum £50 recommended)
- [ ] Check API credentials are valid (certificate uploaded, app key active)
- [ ] Confirm configuration settings in `config.yaml`
  - Kelly factor: 0.25 (quarter Kelly, optimal from validation)
  - Min edge: 0.05 (5% minimum advantage required)
  - Dynamic stake scaling: 3% (<£100), 4% (£100-200), 5% (>£200)
- [ ] Review recent alerts/issues from previous session
- [ ] Verify system time is synchronized
- [ ] Check disk space is adequate for logs

### Startup Procedure

**Option 1: Simulated Mode (Testing)**
```powershell
# Activate virtual environment
.venv\Scripts\Activate.ps1

# Run with simulation
python main.py --simulate --iterations 1000

# Monitor output for errors
```

**Option 2: Live Mode (Real API)**
```powershell
# Activate virtual environment
.venv\Scripts\Activate.ps1

# Verify configuration
python -c "from main import load_config; cfg=load_config(); print(f'Balance: £{cfg[\"bot\"][\"start_balance\"]}, Edge: {cfg[\"bot\"][\"min_edge\"]}')"

# Start bot
python main.py

# Bot will connect to Betfair API and begin trading
```

**Option 3: Dry-Run Mode (Real API, No Bets)**
```powershell
python scripts\dry_run_real_api.py
```

### Post-Startup Verification
- Monitor first 5-10 iterations for normal operation
- Verify bets are being placed (if opportunities exist)
- Check Prometheus metrics endpoint: http://localhost:9151/metrics
- Review initial log entries for warnings/errors

---

## Stopping the Bot

### Graceful Shutdown
1. Press `Ctrl+C` in the terminal
2. Bot will complete current iteration
3. Wait for "Shutting down gracefully..." message
4. Verify all active bets are recorded
5. Check final balance in logs

### Emergency Stop
If graceful shutdown hangs:
1. Press `Ctrl+C` again (force quit)
2. If running as PowerShell background job:
   ```powershell
   # List running jobs
   Get-Job
   
   # Stop specific job
   Stop-Job -Id <JobId>
   
   # Remove job
   Remove-Job -Id <JobId>
   ```
3. Check active bets manually: review last log entries
4. Record current balance before restart
5. Investigate cause of hang

### Post-Shutdown Tasks
- [ ] Review session performance summary
- [ ] Save/backup log files if needed
- [ ] Check for any unresolved bets
- [ ] Note final balance for reconciliation

---

## Monitoring Operations

### Real-Time Monitoring
```powershell
# Start monitoring dashboard
python scripts\monitoring.py

# Quick progress check (for running simulations)
python scripts\check_progress.py
```

Dashboard shows:
- Current balance and P&L
- ROI and drawdown
- Betting activity (win rate, stake analysis)
- Dynamic scaling tier (3%/4%/5% based on balance)
- System health
- Recent alerts

**Balance Tiers (Dynamic Scaling):**
- **£0-99:** Conservative 3% max stake
- **£100-199:** Moderate 4% max stake
- **£200+:** Aggressive 5% max stake

### Metrics Monitoring
```powershell
# Check Prometheus metrics
curl http://localhost:9151/metrics

# Key metrics:
# - bets_placed_total
# - bets_won_total
# - balance_pounds
# - opportunities_found_total
```

### Log Monitoring
```powershell
# Follow live logs
Get-Content -Path "logs\bot.log" -Wait -Tail 50

# Search for errors
Select-String -Path "logs\bot.log" -Pattern "ERROR|CRITICAL"

# Check alerts
Get-Content "alerts.log" -Tail 20
```

---

## Error Handling

### Common Errors and Responses

#### API Authentication Failure (401/403)
**Symptoms:** `AuthenticationError`, `INVALID_SESSION_INFORMATION`

**Actions:**
1. Verify certificate is uploaded to Betfair account
2. Check app key is active (not expired/revoked)
3. Regenerate session token:
   ```powershell
   python scripts\manage_app_keys.py
   ```
4. Restart bot

#### Connection Timeout
**Symptoms:** `requests.exceptions.Timeout`, `Connection timed out`

**Actions:**
1. Check internet connection
2. Verify Betfair API status: https://status.betfair.com
3. Wait 1-2 minutes, retry
4. If persistent, switch to backup network/VPN

#### Insufficient Funds
**Symptoms:** `INSUFFICIENT_FUNDS`, Balance < stake

**Actions:**
1. Stop bot immediately
2. Review recent P&L
3. Deposit additional funds if desired
4. Update `start_balance` in config.yaml
5. Restart bot

#### Rate Limiting (429)
**Symptoms:** `Too Many Requests`, 429 status code

**Actions:**
1. Bot will automatically back off (exponential delay)
2. Monitor for resolution (usually 1-5 minutes)
3. If persistent >10 minutes, contact Betfair support

#### Market Not Available
**Symptoms:** `MARKET_NOT_OPEN_FOR_BETTING`, `NO_CHANNEL_AVAILABLE`

**Actions:**
1. Normal during shoe resets or table closures
2. Bot will retry automatically
3. If >30 minutes, check Betfair for scheduled maintenance

---

## Recovery Procedures

### Crash Recovery

If bot crashes unexpectedly:

1. **Assess State**
   ```powershell
   # Check last 50 log lines
   Get-Content -Path "logs\bot.log" -Tail 50
   
   # Look for exception traceback
   Select-String -Path "logs\bot.log" -Pattern "Traceback" -Context 0,20
   ```

2. **Verify Balance**
   - Log into Betfair manually
   - Check current account balance
   - Compare with last recorded balance in logs

3. **Check Active Bets**
   - Review "My Bets" section on Betfair
   - Note any unsettled bets
   - Wait for settlement before restarting

4. **Restart**
   ```powershell
   # Update config with current balance
   python -c "import yaml; cfg=yaml.safe_load(open('config.yaml')); cfg['bot']['start_balance']=CURRENT_BALANCE; yaml.dump(cfg, open('config.yaml','w'))"
   
   # Restart bot
   python main.py
   ```

### Database/State Corruption

If balance or bet tracking seems incorrect:

1. **Stop bot immediately**
2. **Manual reconciliation:**
   - Get actual balance from Betfair
   - Review all bets from today in Betfair "My Bets"
   - Calculate expected balance = start_balance + sum(profits)
3. **Reset state:**
   - Update `start_balance` in config.yaml to actual balance
   - Clear any cached state (if applicable)
   - Restart with verified balance

### Network Interruption

If network drops during operation:

1. Bot will retry automatically (exponential backoff)
2. Monitor for "Connection restored" message
3. Verify no bets were lost:
   - Check logs for last bet placed
   - Verify in Betfair interface
4. If reconnection fails >5 minutes:
   - Stop bot
   - Check network/VPN
   - Restart when stable

---

## Daily Maintenance

### Morning Startup
```powershell
# 1. Generate yesterday's report
python scripts\reporting.py

# 2. Review performance
cat reports\daily_report_*.txt

# 3. Check for alerts
cat alerts.log

# 4. Start bot
python main.py
```

### Evening Shutdown
```powershell
# 1. Stop bot gracefully (Ctrl+C)

# 2. Generate end-of-day report
python scripts\reporting.py

# 3. Backup logs
Copy-Item logs\bot.log "logs\bot_$(Get-Date -Format 'yyyyMMdd').log"

# 4. Review performance metrics
python scripts\performance_analyzer.py
```

### Weekly Tasks
- [ ] Run comprehensive performance analysis
- [ ] Review configuration optimization results
- [ ] Check for software updates
- [ ] Rotate old log files (keep last 30 days)
- [ ] Backup configuration files
- [ ] Review Betfair account status

### Monthly Tasks
- [ ] Full bankroll audit/reconciliation
- [ ] Review and update risk parameters if needed
- [ ] Analyze edge statistics and market conditions
- [ ] Check certificate expiry (renew if <60 days remaining)
- [ ] Update dependencies: `pip install --upgrade -r requirements.txt`

---

## Troubleshooting

### Bot Not Placing Bets

**Check:**
1. Are opportunities being found? (Check "Opportunities found: X" in logs)
2. Is edge threshold too high? (config: `min_edge` = 0.05 recommended)
3. Is balance insufficient? (stake too large for remaining balance)
4. Is exposure limit reached? (config: `max_exposure_pct` = 0.10 recommended)
5. Is dynamic scaling limiting stakes? Check current tier:
   - <£100: Max 3% of balance
   - £100-200: Max 4% of balance
   - >£200: Max 5% of balance
6. Are calculated stakes exceeding config `max_stake_pct`? (should be 0.05)

**Debug:**
```powershell
# Run with verbose logging
python main.py --simulate --iterations 100 2>&1 | Select-String "edge|opportunity"
```

### Performance Below Expectations

**Investigate:**
1. Check actual edge vs expected:
   ```powershell
   python scripts\performance_analyzer.py
   ```
2. Review market conditions (high variance periods)
3. Compare current config vs optimal:
   ```powershell
   python scripts\config_optimizer.py
   ```
4. Verify true probabilities are accurate (model drift?)

### High Drawdown

**Actions:**
1. Stop bot if drawdown >25%
2. Review recent losing streak:
   ```powershell
   Select-String -Path "logs\bot.log" -Pattern "LOST" | Select-Object -Last 20
   ```
3. Check if market conditions changed
4. Consider reducing `max_stake_pct` temporarily
5. Run validation tests before resuming

### Memory/CPU Issues

**Symptoms:** Slow performance, high resource usage

**Fix:**
```powershell
# Check memory usage
Get-Process python | Select-Object WS,CPU

# Restart bot
Ctrl+C
python main.py

# If persistent, review code for memory leaks
# Check deque sizes, clear old data
```

---

## Recent Configuration Updates

**February 2026 - Optimization Results:**

1. **Kelly Factor: 0.25 (Quarter Kelly)**
   - Extended validation showed +1,243% ROI vs +574% for half Kelly
   - 2.16x performance improvement
   - Lower variance, higher long-term growth

2. **Dynamic Stake Scaling Implemented**
   - Replaces fixed 3% max stake
   - Automatically adjusts risk as bankroll grows
   - Conservative start (3%) → Moderate (4%) → Aggressive (5%)

3. **Minimum Edge: 0.05**
   - Optimal threshold from parameter sweep testing
   - 5% minimum advantage required for bet placement
   - Balance between frequency and profitability

4. **Current Configuration (config.yaml):**
   ```yaml
   bot:
     min_edge: 0.05
     max_exposure_pct: 0.10
     max_stake_pct: 0.05  # Dynamic scaling overrides this
     kelly_factor: 0.25
     start_balance: 50
   ```

5. **Validation Results:**
   - 10,000 iteration testing: +1,243% average ROI
   - All 36 configurations tested were profitable
   - Consistency: High (8.4% standard deviation)
   - £50 starting bankroll validated: +296% in 2-hour test

---

## Contact Information

- **Betfair Support:** support@betfair.com, +44 (0) 207 170 7775
- **API Status:** https://status.betfair.com
- **Documentation:** https://docs.developer.betfair.com

---

## Quick Reference Commands

```powershell
# Start simulation
python main.py --simulate --iterations 1000

# Start live
python main.py

# Check current progress (running simulations)
python scripts\check_progress.py

# Monitor performance
python scripts\monitoring.py

# Generate report
python scripts\reporting.py

# Run validation tests (10k iterations)
python scripts\extended_validation.py

# Optimize config (tests 81 combinations, ~2 hours)
python scripts\config_optimizer.py

# Analyze performance (Sharpe/Sortino ratios)
python scripts\performance_analyzer.py validation_results_*.json

# Check metrics
curl http://localhost:9151/metrics

# Follow logs
Get-Content -Path "logs\bot.log" -Wait -Tail 50

# Search for errors
Select-String -Path "logs\bot.log" -Pattern "ERROR"

# Manage background jobs
Get-Job | Format-List
Stop-Job -Id <JobId>
Remove-Job -Id <JobId>
```

---

**Last Updated:** February 2, 2026
**Version:** 1.1 - Added dynamic scaling, recent optimizations, and enhanced monitoring
