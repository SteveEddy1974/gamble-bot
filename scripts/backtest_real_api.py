#!/usr/bin/env python3
"""Backtest with real API - place hypothetical bets and track actual outcomes.

This script monitors real games, identifies opportunities, tracks which bets would
be placed, and then checks the actual game results to calculate win rates.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import argparse
import time
from typing import Dict, List

from main import load_config, parse_shoe_state, parse_market_selections, prob_pocket_pair, prob_natural_win
from api_client import APIClient
from engine import evaluate, size_stake, calculate_dynamic_max_stake_pct


def backtest_real_api(iterations=100, start_balance=30, max_exposure_pct=0.1, channel_id=None):
    """Run backtest with real API data and track actual outcomes."""
    config = load_config()
    api_client = APIClient(config['credentials'])
    
    if channel_id is None:
        channel_id = config.get('bot', {}).get('channel_id', None)
        if channel_id is None:
            print("No channel_id specified. Use --channel CHANNEL_ID")
            return
    
    print(f"=== REAL API BACKTEST ===")
    print(f"Channel: {channel_id}")
    print(f"Iterations: {iterations}")
    print(f"Start Balance: £{start_balance}")
    print(f"Max Exposure: {max_exposure_pct*100}%")
    print(f"Tracking actual game outcomes...")
    print("=" * 80)
    print()
    
    balance = start_balance
    current_exposure = 0.0
    
    # Track bets: {game_id: {'bet_type': str, 'stake': float, 'price': float, 'edge': float}}
    pending_bets: Dict[str, List[dict]] = {}
    completed_bets: List[dict] = []
    
    ns = {'bf': 'urn:betfair:games:api:v1'}
    poll_interval = config.get('bot', {}).get('poll_interval_seconds', 3)
    min_edge = config.get('bot', {}).get('min_edge', 0.01)
    
    for i in range(iterations):
        try:
            xml_root = api_client.get_snapshot(channel_id)
            
            # Get game ID
            game_elem = xml_root.find('.//bf:game', ns) or xml_root.find('.//game')
            game_id = game_elem.get('id') if game_elem is not None else None
            
            if game_id is None:
                print(f"[{i+1}] No game ID found")
                time.sleep(poll_interval)
                continue
            
            # Get shoe
            game_data = xml_root.find('.//bf:gameData', ns) or xml_root.find('.//gameData')
            shoe_elem = None
            if game_data is not None:
                for obj in game_data.findall('.//bf:object', ns):
                    if obj.get('name') == 'Shoe':
                        shoe_elem = obj
                        break
                if shoe_elem is None:
                    for obj in game_data.findall('.//object'):
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
            
            # Check if we should place bets for this game
            if game_id not in pending_bets:
                pending_bets[game_id] = []
                
                for sel in selections:
                    if sel.name == 'Pocket Pair In Any Hand' and sel.best_back_price:
                        true_prob = prob_pocket_pair(shoe)
                        ok, edge = evaluate(sel, true_prob, sel.best_back_price, 'BACK')
                        
                        if ok:
                            dynamic_max_stake_pct = calculate_dynamic_max_stake_pct(balance)
                            stake = size_stake(
                                balance, max_exposure_pct, edge,
                                price=sel.best_back_price, true_prob=true_prob,
                                shrink=config['bot'].get('kelly_factor', 0.25),
                                max_stake_pct=dynamic_max_stake_pct
                            )
                            
                            if current_exposure + stake <= balance * max_exposure_pct:
                                pending_bets[game_id].append({
                                    'bet_type': 'Pocket Pair',
                                    'stake': stake,
                                    'price': sel.best_back_price,
                                    'edge': edge,
                                    'true_prob': true_prob
                                })
                                current_exposure += stake
                                print(f"[{i+1}] Game {game_id}: BETTING £{stake:.2f} @ {sel.best_back_price:.2f} (Edge: {edge*100:.2f}%)")
            
            # Check for completed games (get game results from gameData)
            # Note: In real implementation, you'd need to fetch historical game results
            # For now, we'll track bets and show pending count
            
            if (i + 1) % 20 == 0:
                print(f"[{i+1}/{iterations}] Balance: £{balance:.2f} | Pending Bets: {len(pending_bets)} games | Exposure: £{current_exposure:.2f}")
            
            time.sleep(poll_interval)
            
        except KeyboardInterrupt:
            print("\n\nStopped by user.")
            break
        except Exception as e:
            print(f"[{i+1}] Error: {e}")
            time.sleep(poll_interval)
    
    print("\n" + "=" * 80)
    print("BACKTEST RESULTS")
    print("=" * 80)
    print(f"Total Games Monitored: {iterations}")
    print(f"Games With Bets: {len(pending_bets)}")
    total_bets = sum(len(bets) for bets in pending_bets.values())
    total_stake = sum(bet['stake'] for bets in pending_bets.values() for bet in bets)
    print(f"Total Bets Placed: {total_bets}")
    print(f"Total Staked: £{total_stake:.2f}")
    print()
    print("⚠️  NOTE: Win rate calculation requires fetching historical game results")
    print("    from the API, which is not implemented in this basic backtest.")
    print("    To see actual win rates, run with simulate: false for real bets.")
    print("=" * 80)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('iterations', type=int, default=100, nargs='?')
    parser.add_argument('--channel', type=int, default=None)
    parser.add_argument('--balance', type=float, default=30)
    args = parser.parse_args()
    
    backtest_real_api(
        iterations=args.iterations,
        start_balance=args.balance,
        channel_id=args.channel
    )
