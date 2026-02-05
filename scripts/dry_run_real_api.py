#!/usr/bin/env python3
"""Real API dry-run harness to test with live market data WITHOUT placing real bets.

This script connects to the actual Betfair API and evaluates opportunities on real
market data, but does not execute any bet orders. Perfect for validating the bot's
behavior on live markets before going into production.

Usage: python scripts/dry_run_real_api.py [iterations] [--channel CHANNEL_ID]
"""
import sys
import os
import argparse
import time
# ensure project root is on path when executed from scripts/
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import parse_shoe_state, parse_market_selections, prob_pocket_pair, prob_natural_win, BetManager, load_config
from engine import evaluate, size_stake, calculate_dynamic_max_stake_pct
from api_client import APIClient


def _selection_records(selections, shoe):
    records = []
    for sel in selections:
        if sel.status != 'IN_PLAY' or not sel.best_back_price:
            continue
        if sel.name == 'Pocket Pair In Any Hand':
            true_prob = prob_pocket_pair(shoe)
        elif sel.name == 'Natural Win':
            true_prob = prob_natural_win(shoe)
        else:
            continue
        records.append({
            'name': sel.name,
            'selection_id': sel.selection_id,
            'price': sel.best_back_price,
            'true_prob': true_prob,
        })
    return records


def _eval_strategy(records, start_balance, max_exposure_pct, min_edge, min_price, kelly_factor, trade_natural, trade_pocket):
    bet_manager = BetManager(start_balance, start_balance * max_exposure_pct)
    stats = {
        'opportunities_found': 0,
        'would_place': 0,
        'would_skip_exposure': 0,
        'would_skip_balance': 0,
        'total_would_stake': 0.0,
        'avg_true_prob': 0.0,
        'avg_edge': 0.0,
    }
    true_prob_sum = 0.0
    edge_sum = 0.0

    for rec in records:
        if rec['name'] == 'Pocket Pair In Any Hand' and not trade_pocket:
            continue
        if rec['name'] == 'Natural Win' and not trade_natural:
            continue
        if min_price is not None and rec['price'] < min_price:
            continue

        ok, edge = evaluate(None, rec['true_prob'], rec['price'], 'BACK', min_edge=min_edge)
        if not ok:
            continue
        stats['opportunities_found'] += 1
        dynamic_max_stake_pct = calculate_dynamic_max_stake_pct(bet_manager.balance)
        stake = size_stake(
            bet_manager.balance,
            max_exposure_pct,
            edge,
            price=rec['price'],
            true_prob=rec['true_prob'],
            shrink=kelly_factor,
            max_stake_pct=dynamic_max_stake_pct,
        )

        can_place = bet_manager.can_place(stake)
        if can_place:
            stats['would_place'] += 1
            stats['total_would_stake'] += stake
            true_prob_sum += rec['true_prob']
            edge_sum += edge
        else:
            if stake > bet_manager.balance:
                stats['would_skip_balance'] += 1
            else:
                stats['would_skip_exposure'] += 1

    if stats['would_place']:
        stats['avg_true_prob'] = true_prob_sum / stats['would_place']
        stats['avg_edge'] = edge_sum / stats['would_place']
    return stats


def run_real_api_dry(
    iterations=100,
    start_balance=1000,
    max_exposure_pct=0.1,
    channel_id=None,
    min_edge=None,
    min_price=None,
    kelly_factor=None,
    trade_natural=True,
    trade_pocket=True,
    sweep=False,
):
    """
    Connect to real Betfair API and evaluate opportunities without placing bets.
    
    Args:
        iterations: Number of polling cycles to run
        start_balance: Starting balance for simulation
        max_exposure_pct: Max exposure as percentage of balance
        channel_id: Specific channel ID to monitor (if None, uses config default or prompts)
    """
    config = load_config()
    
    # Initialize real API client
    api_client = APIClient(config['credentials'])
    bet_manager = BetManager(start_balance, start_balance * max_exposure_pct)
    
    # Determine channel to monitor
    if channel_id is None:
        # Try to get from config or use a default
        channel_id = config.get('bot', {}).get('channel_id', None)
        if channel_id is None:
            print("No channel_id specified. Please provide --channel CHANNEL_ID")
            print("Example: python scripts/dry_run_real_api.py 100 --channel 12345")
            return
    
    print(f"=== REAL API DRY-RUN MODE ===")
    print(f"Channel: {channel_id}")
    print(f"Iterations: {iterations}")
    print(f"Start Balance: £{start_balance}")
    print(f"Max Exposure: {max_exposure_pct*100}%")
    print(f"IMPORTANT: NO REAL BETS WILL BE PLACED")
    print("=" * 50)
    print()
    
    stats = {
        'opportunities_found': 0,
        'would_place': 0,
        'would_skip_exposure': 0,
        'would_skip_balance': 0,
        'api_errors': 0,
        'total_would_stake': 0.0
    }
    min_edge = min_edge if min_edge is not None else config['bot'].get('min_edge', 0.05)
    min_price = min_price if min_price is not None else config['bot'].get('min_price')
    kelly_factor = kelly_factor if kelly_factor is not None else config['bot'].get('kelly_factor', 0.25)
    trade_natural = trade_natural if trade_natural is not None else config['bot'].get('trade_natural_win', True)
    trade_pocket = trade_pocket if trade_pocket is not None else config['bot'].get('trade_pocket_pair', True)

    all_records = []
    
    poll_interval = config.get('bot', {}).get('poll_interval_seconds', 3)
    prev_cards_remaining = None
    
    for i in range(iterations):
        try:
            # Fetch real market snapshot
            xml_root = api_client.get_snapshot(channel_id)
            
            # Define namespace
            ns = {'bf': 'urn:betfair:games:api:v1'}
            
            # Parse shoe state from gameData/object[@name='Shoe']
            game_data = xml_root.find('.//bf:gameData', ns)
            if game_data is None:
                game_data = xml_root.find('.//gameData')
            
            shoe_elem = None
            if game_data is not None:
                for obj in game_data.findall('.//bf:object', ns):
                    if obj.get('name') == 'Shoe':
                        shoe_elem = obj
                        break
                # Try without namespace if not found
                if shoe_elem is None:
                    for obj in game_data.findall('.//object'):
                        if obj.get('name') == 'Shoe':
                            shoe_elem = obj
                            break
            
            if shoe_elem is None:
                print(f"[{i+1}] No shoe data available")
                time.sleep(poll_interval)
                continue
            
            shoe = parse_shoe_state(shoe_elem)
            
            # Detect shoe resets
            if prev_cards_remaining is not None and prev_cards_remaining < 100 and shoe.cards_remaining >= 400:
                print(f"[{i+1}] 🔄 SHOE RESET detected ({prev_cards_remaining} -> {shoe.cards_remaining})")
            prev_cards_remaining = shoe.cards_remaining
            
            # Parse market selections from markets/market/selections
            markets = xml_root.find('.//bf:markets', ns)
            if markets is None:
                markets = xml_root.find('.//markets')
            
            market = None
            if markets is not None:
                for m in markets.findall('.//bf:market', ns) or markets.findall('.//market'):
                    sel_elem = m.find('.//bf:selections', ns)
                    if sel_elem is None:
                        sel_elem = m.find('.//selections')
                    if sel_elem is not None and sel_elem.get('type') == 'SideBets':
                        market = m
                        break
                if market is None:
                    market = markets.find('.//bf:market', ns) or markets.find('.//market')
            
            selections_elem = None
            if market is not None:
                selections_elem = market.find('.//bf:selections', ns)
                if selections_elem is None:
                    selections_elem = market.find('.//selections')
            
            if selections_elem is None:
                print(f"[{i+1}] No market selections available")
                time.sleep(poll_interval)
                continue
            
            selections = parse_market_selections(selections_elem)
            all_records.extend(_selection_records(selections, shoe))
            
            # Progress indicator
            if (i + 1) % 10 == 0:
                print(f"[{i+1}/{iterations}] Cards: {shoe.cards_remaining}, Opportunities: {stats['opportunities_found']}, Would Place: {stats['would_place']}")
            
            # Evaluate opportunities (just like production, but don't place bets)
            for rec in _selection_records(selections, shoe):
                if rec['name'] == 'Pocket Pair In Any Hand' and not trade_pocket:
                    continue
                if rec['name'] == 'Natural Win' and not trade_natural:
                    continue
                if min_price is not None and rec['price'] < min_price:
                    continue

                ok, edge = evaluate(None, rec['true_prob'], rec['price'], 'BACK', min_edge=min_edge)
                if ok:
                    stats['opportunities_found'] += 1
                    dynamic_max_stake_pct = calculate_dynamic_max_stake_pct(bet_manager.balance)
                    stake = size_stake(
                        bet_manager.balance,
                        max_exposure_pct,
                        edge,
                        price=rec['price'],
                        true_prob=rec['true_prob'],
                        shrink=kelly_factor,
                        max_stake_pct=dynamic_max_stake_pct
                    )

                    can_place = bet_manager.can_place(stake)
                    if can_place:
                        stats['would_place'] += 1
                        stats['total_would_stake'] += stake
                        print(f"[{i+1}] ✓ WOULD PLACE BET: {rec['name']}")
                        print(f"      Edge: {edge*100:+.2f}% | Price: {rec['price']:.3f} | True Prob: {rec['true_prob']:.3f}")
                        print(f"      Stake: £{stake:.2f} | Balance: £{bet_manager.balance:.2f} | Exposure: £{bet_manager.current_exposure:.2f}")
                    else:
                        if stake > bet_manager.balance:
                            stats['would_skip_balance'] += 1
                            reason = "insufficient balance"
                        else:
                            stats['would_skip_exposure'] += 1
                            reason = "max exposure reached"
                        print(f"[{i+1}] ✗ WOULD SKIP: {rec['name']} ({reason})")
            
            time.sleep(poll_interval)
            
        except Exception as e:
            stats['api_errors'] += 1
            print(f"[{i+1}] ❌ API Error: {e}")
            time.sleep(poll_interval)
            continue
    
    # Summary
    print()
    print("=" * 50)
    print("DRY-RUN SUMMARY (Real API, No Bets Placed)")
    print("=" * 50)
    print(f"Total Iterations: {iterations}")
    print(f"Opportunities Found: {stats['opportunities_found']}")
    print(f"Would Place: {stats['would_place']}")
    print(f"Skipped (Exposure): {stats['would_skip_exposure']}")
    print(f"Skipped (Balance): {stats['would_skip_balance']}")
    print(f"Total Would Stake: £{stats['total_would_stake']:.2f}")
    print(f"API Errors: {stats['api_errors']}")
    print(f"Final Balance: £{bet_manager.balance:.2f} (unchanged - no real bets)")
    print("=" * 50)

    if sweep and all_records:
        print()
        print("=" * 50)
        print("STRATEGY SWEEP (Expected Win-Rate Proxy)")
        print("=" * 50)
        min_edges = [0.05, 0.08, 0.12]
        min_prices = [None, 6.0, 8.0]
        kelly_factors = [0.05, 0.10]
        candidates = []
        for me in min_edges:
            for mp in min_prices:
                for kf in kelly_factors:
                    s = _eval_strategy(
                        all_records,
                        start_balance,
                        max_exposure_pct,
                        me,
                        mp,
                        kf,
                        trade_natural,
                        trade_pocket,
                    )
                    if s['would_place'] == 0:
                        continue
                    candidates.append((me, mp, kf, s))

        if not candidates:
            print("No strategies produced any bets.")
            return

        candidates.sort(key=lambda x: (x[3]['avg_true_prob'], x[3]['avg_edge']), reverse=True)
        for me, mp, kf, s in candidates[:5]:
            print(
                f"min_edge={me:.2f} min_price={mp} kelly={kf:.2f} | "
                f"bets={s['would_place']} avg_true_prob={s['avg_true_prob']:.3f} avg_edge={s['avg_edge']:.3f}"
            )
        best = candidates[0]
        print(
            f"\nSuggested sweet spot: min_edge={best[0]:.2f}, min_price={best[1]}, kelly={best[2]:.2f}"
        )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Real API dry-run without placing bets')
    parser.add_argument('iterations', type=int, nargs='?', default=100, 
                       help='Number of polling cycles to run (default: 100)')
    parser.add_argument('--channel', type=str, default=None,
                       help='Channel ID to monitor (e.g., 12345)')
    parser.add_argument('--balance', type=float, default=1000,
                       help='Starting balance (default: 1000)')
    parser.add_argument('--exposure', type=float, default=0.1,
                       help='Max exposure as decimal (default: 0.1 = 10%%)')
    parser.add_argument('--min-edge', type=float, default=None,
                       help='Minimum edge threshold (default: config min_edge)')
    parser.add_argument('--min-price', type=float, default=None,
                       help='Minimum price threshold (default: config min_price)')
    parser.add_argument('--kelly-factor', type=float, default=None,
                       help='Kelly shrink factor (default: config kelly_factor)')
    parser.add_argument('--trade-natural', action='store_true',
                       help='Enable Natural Win selection (default: config)')
    parser.add_argument('--trade-pocket', action='store_true',
                       help='Enable Pocket Pair selection (default: config)')
    parser.add_argument('--sweep', action='store_true',
                       help='Run a strategy sweep after collecting data')
    
    args = parser.parse_args()
    
    run_real_api_dry(
        iterations=args.iterations,
        start_balance=args.balance,
        max_exposure_pct=args.exposure,
        channel_id=args.channel,
        min_edge=args.min_edge,
        min_price=args.min_price,
        kelly_factor=args.kelly_factor,
        trade_natural=args.trade_natural or None,
        trade_pocket=args.trade_pocket or None,
        sweep=args.sweep,
    )
