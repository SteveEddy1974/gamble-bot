#!/usr/bin/env python3
"""Live opportunity monitor - shows betting alerts in real-time."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import time
from datetime import datetime
import platform

from main import load_config, parse_shoe_state, parse_market_selections, prob_pocket_pair, prob_natural_win
from api_client import APIClient
from engine import evaluate, size_stake, calculate_dynamic_max_stake_pct
import subprocess
import shlex
import json

# Notifications: attempt to use Windows toast notifications if available (win10toast),
# otherwise fall back to audible beep using winsound on Windows or a short print alert.
try:
    from win10toast import ToastNotifier
    _TOASTER = ToastNotifier()
except Exception:
    _TOASTER = None

try:
    if platform.system() == 'Windows':
        import winsound
    else:
        winsound = None
except Exception:
    winsound = None


def notify_user(title: str, message: str):
    """Show desktop toast if available, otherwise play audible beep/fallback print."""
    try:
        if _TOASTER is not None:
            # Use Toast notification on Windows
            _TOASTER.show_toast(title, message, duration=5, threaded=True)
            return
    except Exception:
        pass

    try:
        if winsound is not None:
            # Simple audible pattern: 3 short beeps
            for f, ms in ((1000, 120), (1500, 120), (1200, 120)):
                winsound.Beep(f, ms)
            return
    except Exception:
        pass

    # Fallback textual alert
    print(f"*** NOTIFICATION: {title} - {message}")

def monitor_opportunities(channel_id=None, balance=30):
    """Monitor and display betting opportunities in real-time."""
    config = load_config()
    api_client = APIClient(config['credentials'])
    
    if channel_id is None:
        channel_id = config.get('bot', {}).get('channel_id', 1444086)
    
    min_edge = config.get('bot', {}).get('min_edge', 0.01)
    max_exposure_pct = config.get('bot', {}).get('max_exposure_pct', 0.10)
    kelly_factor = config.get('bot', {}).get('kelly_factor', 0.25)
    
    print("=" * 80)
    print("🎯 LIVE OPPORTUNITY MONITOR")
    print("=" * 80)
    print(f"Channel: {channel_id} (Exchange Baccarat)")
    print(f"Balance: £{balance}")
    print(f"Min Edge: {min_edge*100}%")
    print("Monitoring... Press Ctrl+C to stop")
    # Notification status
    if _TOASTER is not None:
        print("Notifications: Desktop toasts enabled (win10toast)")
    elif winsound is not None:
        print("Notifications: Audible beeps enabled (winsound)")
    else:
        print("Notifications: Desktop/audio not available; textual alerts only")
    print("=" * 80)
    print()
    
    ns = {'bf': 'urn:betfair:games:api:v1'}
    poll_interval = 3
    last_alert_time = {}
    last_status_time = 0
    check_count = 0
    
    try:
        while True:
            try:
                check_count += 1
                xml_root = api_client.get_snapshot(channel_id)
                
                # Check market status
                market = xml_root.find('.//bf:market', ns)
                if market is None:
                    market = xml_root.find('.//market')
                
                market_status = "UNKNOWN"
                if market is not None:
                    status_elem = market.find('.//bf:status', ns)
                    if status_elem is None:
                        status_elem = market.find('.//status')
                    if status_elem is not None:
                        market_status = status_elem.text
                
                # Show periodic status updates (every 20 seconds)
                now = time.time()
                if now - last_status_time > 20:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"[{timestamp}] Monitoring... (checks: {check_count}, status: {market_status})")
                    last_status_time = now
                
                # Get shoe
                game_data = xml_root.find('.//bf:gameData', ns)
                if game_data is None:
                    game_data = xml_root.find('.//gameData')
                
                shoe_elem = None
                if game_data is not None:
                    for obj in game_data.findall('.//bf:object', ns):
                        if obj.get('name') == 'Shoe':
                            shoe_elem = obj
                            break
                
                if shoe_elem is None:
                    time.sleep(poll_interval)
                    continue
                
                shoe = parse_shoe_state(shoe_elem)
                
                # Get selections
                markets = xml_root.find('.//bf:markets', ns)
                if markets is None:
                    markets = xml_root.find('.//markets')
                
                market = None
                if markets is not None:
                    market = markets.find('.//bf:market', ns)
                    if market is None:
                        market = markets.find('.//market')
                
                selections_elem = None
                if market is not None:
                    selections_elem = market.find('.//bf:selections', ns)
                    if selections_elem is None:
                        selections_elem = market.find('.//selections')
                
                if selections_elem is None:
                    time.sleep(poll_interval)
                    continue
                
                selections = parse_market_selections(selections_elem)
                
                # Check for opportunities
                for sel in selections:
                    if sel.status != 'IN_PLAY':
                        continue
                    
                    opportunity = None
                    bet_type = None
                    
                    if sel.name == 'Pocket Pair In Any Hand' and sel.best_back_price:
                        true_prob = prob_pocket_pair(shoe)
                        ok, edge = evaluate(sel, true_prob, sel.best_back_price, 'BACK')
                        if ok:
                            bet_type = 'Pocket Pair'
                            opportunity = {
                                'name': sel.name,
                                'price': sel.best_back_price,
                                'true_prob': true_prob,
                                'edge': edge
                            }
                    
                    elif sel.name == 'Natural Hand Win Any Hand' and sel.best_back_price:
                        true_prob = prob_natural_win(shoe)
                        ok, edge = evaluate(sel, true_prob, sel.best_back_price, 'BACK')
                        if ok:
                            bet_type = 'Natural Win'
                            opportunity = {
                                'name': sel.name,
                                'price': sel.best_back_price,
                                'true_prob': true_prob,
                                'edge': edge
                            }
                    
                    if opportunity:
                        # Throttle alerts - only show each bet type once per 10 seconds
                        now = time.time()
                        if bet_type in last_alert_time and now - last_alert_time[bet_type] < 10:
                            continue
                        
                        last_alert_time[bet_type] = now
                        
                        # Calculate stake
                        dynamic_max_stake_pct = calculate_dynamic_max_stake_pct(balance)
                        stake = size_stake(
                            balance, max_exposure_pct, opportunity['edge'],
                            price=opportunity['price'], true_prob=opportunity['true_prob'],
                            shrink=kelly_factor, max_stake_pct=dynamic_max_stake_pct
                        )
                        
                        # Display alert
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        print("\n" + "="*80)
                        print(f"🚨 OPPORTUNITY FOUND @ {timestamp}")
                        print("="*80)
                        print(f"  Bet: {bet_type}")
                        print(f"  Price: {opportunity['price']:.2f}")
                        print(f"  True Prob: {opportunity['true_prob']*100:.2f}%")
                        print(f"  Edge: {opportunity['edge']*100:.2f}%")
                        print(f"  Recommended Stake: £{stake:.2f}")
                        print(f"  Cards Remaining: {shoe.cards_remaining}")
                        print("="*80)
                        print("➡️  Go to: https://games.betfair.com/exchange-baccarat/")
                        print(f"➡️  Place BACK bet: £{stake:.2f} @ {opportunity['price']:.2f}")
                        print("="*80 + "\n")

                        # Notify user (desktop + audible fallback)
                        title = f"Opportunity: {bet_type} @ {opportunity['price']:.2f}"
                        message = f"Stake: £{stake:.2f} — Edge: {opportunity['edge']*100:.2f}% — Cards: {shoe.cards_remaining}"
                        notify_user(title, message)

                        # Optionally invoke UI placer (Selenium) - controlled by config
                        bot_cfg = config.get('bot', {})
                        if bot_cfg.get('ui_auto_place'):
                            # Build command args
                            auto_submit_flag = '--auto-submit' if bot_cfg.get('ui_auto_submit') else ''
                            headless_flag = '--headless' if bot_cfg.get('ui_headless') else ''
                            cmd = f"python scripts/selenium_placer.py --bet-type {shlex.quote(bet_type)} --price {opportunity['price']} --stake {stake} {auto_submit_flag} {headless_flag}"
                            print(f"Invoking UI placer: {cmd}")
                            # Fire-and-forget: run in background so monitor continues
                            try:
                                subprocess.Popen(cmd, shell=True)
                            except Exception as e:
                                print(f"Failed to invoke UI placer: {e}")
                
                time.sleep(poll_interval)
                
            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(poll_interval)
    
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")
        print("=" * 80)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--channel', type=int, default=None)
    parser.add_argument('--balance', type=float, default=30)
    args = parser.parse_args()
    
    monitor_opportunities(channel_id=args.channel, balance=args.balance)
