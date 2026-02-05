#!/usr/bin/env python3
"""
Extended validation testing with parameter sweeps.

Tests:
- 10,000 iteration runs for statistical significance
- Different minimum edge thresholds (0.03, 0.05, 0.08)
- Different Kelly shrink factors (0.25, 0.5, 0.75, 1.0)
- Compares full Kelly vs conservative approaches
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import load_config, BetManager, parse_shoe_state, parse_market_selections
from main import prob_natural_win, prob_pocket_pair, evaluate, size_stake, Opportunity
from api_client import SimulatedAPIClient
import time
import logging
from collections import defaultdict
import random
import json
from datetime import datetime

logging.basicConfig(level=logging.WARNING)


def run_validation_test(start_balance, iterations, min_edge, kelly_factor, config):
    """Run single validation test with specific parameters."""
    max_exposure = start_balance * config['bot']['max_exposure_pct']
    bet_manager = BetManager(balance=start_balance, max_exposure=max_exposure)
    
    # Create API client with realistic shoe depletion
    api_client = SimulatedAPIClient(
        start_cards_remaining=416,
        decrement=4,
        reset_after=80,  # Reset every 80 iterations (~320 cards)
        settle_delay=1
    )
    
    bets_placed = 0
    opportunities_found = 0
    opportunities_skipped = 0
    min_balance = start_balance
    max_balance = start_balance
    balance_history = []
    edge_history = []
    stake_history = []
    
    for i in range(iterations):
        xml_root = api_client.get_snapshot(channel_id='123')
        shoe_elem = xml_root.find('shoe')
        selections_elem = xml_root.find('marketSelections')
        shoe = parse_shoe_state(shoe_elem)
        selections = parse_market_selections(selections_elem)
        
        if shoe is None:
            continue
        
        for sel in selections:
            if sel.status != 'IN_PLAY':
                continue
            
            prob = None
            if sel.name == 'Natural Win' and sel.best_back_price:
                prob = prob_natural_win(shoe)
            elif sel.name == 'Pocket Pair In Any Hand' and sel.best_back_price:
                prob = prob_pocket_pair(shoe)
            
            if prob is None:
                continue
            
            ok, edge = evaluate(sel, prob, sel.best_back_price, 'BACK')
            if ok and edge >= min_edge:
                opportunities_found += 1
                edge_history.append(edge)
                
                # Calculate stake with custom Kelly factor
                stake = size_stake(
                    bet_manager.balance,
                    config['bot']['max_exposure_pct'],
                    edge,
                    price=sel.best_back_price,
                    true_prob=prob,
                    max_stake_pct=config['bot'].get('max_stake_pct', 0.03),
                )
                
                # Apply Kelly shrink factor
                stake = stake * kelly_factor
                stake_history.append(stake)
                
                if bet_manager.can_place(stake):
                    opp = Opportunity(sel, prob, sel.best_back_price, edge, 'BACK', stake)
                    bet_id = str(bets_placed + 1)
                    
                    bet_manager.record_accepted(bet_id, opp)
                    bets_placed += 1
                    
                    # Simulate settlement
                    won = random.random() < prob
                    
                    if won:
                        payout = stake * (sel.best_back_price - 1.0)
                        bet_manager.process_settlement(bet_id, 'WON', payout)
                    else:
                        bet_manager.process_settlement(bet_id, 'LOST', 0.0)
                    
                    min_balance = min(min_balance, bet_manager.balance)
                    max_balance = max(max_balance, bet_manager.balance)
                else:
                    opportunities_skipped += 1
        
        # Record balance every 100 iterations
        if i % 100 == 0:
            balance_history.append(bet_manager.balance)
    
    final_balance = bet_manager.balance
    roi = ((final_balance - start_balance) / start_balance) * 100
    drawdown = ((min_balance - start_balance) / start_balance) * 100
    
    return {
        'start_balance': start_balance,
        'final_balance': final_balance,
        'roi': roi,
        'bets_placed': bets_placed,
        'opportunities_found': opportunities_found,
        'opportunities_skipped': opportunities_skipped,
        'min_balance': min_balance,
        'max_balance': max_balance,
        'drawdown': drawdown,
        'balance_history': balance_history,
        'avg_edge': sum(edge_history) / len(edge_history) if edge_history else 0,
        'avg_stake': sum(stake_history) / len(stake_history) if stake_history else 0,
        'max_edge': max(edge_history) if edge_history else 0,
    }


def main():
    config = load_config()
    
    # Test parameters
    start_balance = 1000
    iterations = 10000
    min_edges = [0.03, 0.05, 0.08]
    kelly_factors = [0.25, 0.5, 0.75, 1.0]
    trials_per_config = 3
    
    print("=" * 80)
    print("EXTENDED VALIDATION TESTING")
    print("=" * 80)
    print(f"\nTest Parameters:")
    print(f"  Starting balance: £{start_balance}")
    print(f"  Iterations per trial: {iterations:,}")
    print(f"  Trials per configuration: {trials_per_config}")
    print(f"  Min edges tested: {min_edges}")
    print(f"  Kelly factors tested: {kelly_factors}")
    print(f"  Max exposure: {config['bot']['max_exposure_pct']*100}%")
    print(f"  Max stake per bet: {config['bot'].get('max_stake_pct', 0.03)*100}%")
    print(f"\nTotal tests: {len(min_edges) * len(kelly_factors) * trials_per_config} ({len(min_edges)} edges × {len(kelly_factors)} Kellys × {trials_per_config} trials)")
    print(f"Estimated time: ~{len(min_edges) * len(kelly_factors) * trials_per_config * 2} minutes\n")
    
    all_results = []
    
    for min_edge in min_edges:
        for kelly_factor in kelly_factors:
            print(f"\nTesting min_edge={min_edge:.2f}, Kelly={kelly_factor:.2f}x")
            print("-" * 80)
            
            config_results = []
            
            for trial in range(trials_per_config):
                print(f"  Trial {trial+1}/{trials_per_config}... ", end='', flush=True)
                start_time = time.time()
                
                result = run_validation_test(
                    start_balance,
                    iterations,
                    min_edge,
                    kelly_factor,
                    config
                )
                
                elapsed = time.time() - start_time
                
                result['min_edge'] = min_edge
                result['kelly_factor'] = kelly_factor
                result['trial'] = trial + 1
                result['elapsed_seconds'] = elapsed
                
                config_results.append(result)
                all_results.append(result)
                
                print(f"ROI: {result['roi']:+.1f}% ({result['bets_placed']} bets, {elapsed:.1f}s)")
            
            # Summary for this configuration
            avg_roi = sum(r['roi'] for r in config_results) / len(config_results)
            avg_bets = sum(r['bets_placed'] for r in config_results) / len(config_results)
            avg_edge = sum(r['avg_edge'] for r in config_results) / len(config_results)
            
            print(f"  → Average: ROI {avg_roi:+.1f}%, {avg_bets:.0f} bets, {avg_edge:.3f} edge")
    
    # Overall summary
    print("\n" + "=" * 80)
    print("COMPREHENSIVE SUMMARY")
    print("=" * 80)
    
    # Group by configuration
    by_config = defaultdict(list)
    for r in all_results:
        key = (r['min_edge'], r['kelly_factor'])
        by_config[key].append(r)
    
    print("\nConfiguration Rankings (by average ROI):")
    print("-" * 80)
    print(f"{'Min Edge':<12} {'Kelly':<10} {'Avg ROI':<12} {'Avg Bets':<12} {'Avg Edge':<12} {'Consistency':<12}")
    print("-" * 80)
    
    config_summaries = []
    for (min_edge, kelly_factor), results in by_config.items():
        avg_roi = sum(r['roi'] for r in results) / len(results)
        std_roi = (sum((r['roi'] - avg_roi) ** 2 for r in results) / len(results)) ** 0.5
        avg_bets = sum(r['bets_placed'] for r in results) / len(results)
        avg_edge = sum(r['avg_edge'] for r in results) / len(results)
        
        config_summaries.append({
            'min_edge': min_edge,
            'kelly_factor': kelly_factor,
            'avg_roi': avg_roi,
            'std_roi': std_roi,
            'avg_bets': avg_bets,
            'avg_edge': avg_edge,
        })
    
    # Sort by ROI
    config_summaries.sort(key=lambda x: x['avg_roi'], reverse=True)
    
    for i, cs in enumerate(config_summaries, 1):
        consistency = "High" if cs['std_roi'] < 20 else "Medium" if cs['std_roi'] < 40 else "Low"
        marker = "★" if i == 1 else " "
        print(f"{marker} {cs['min_edge']:<11.2f} {cs['kelly_factor']:<9.2f}x {cs['avg_roi']:+10.1f}% {cs['avg_bets']:>10.0f} {cs['avg_edge']:>11.3f} {consistency:<12}")
    
    # Best configuration
    best = config_summaries[0]
    print("\n" + "=" * 80)
    print("OPTIMAL CONFIGURATION")
    print("=" * 80)
    print(f"  Min Edge: {best['min_edge']:.2f}")
    print(f"  Kelly Factor: {best['kelly_factor']:.2f}x")
    print(f"  Average ROI: {best['avg_roi']:+.1f}%")
    print(f"  Average Bets: {best['avg_bets']:.0f}")
    print(f"  Average Edge: {best['avg_edge']:.3f}")
    print(f"  ROI Std Dev: {best['std_roi']:.1f}%")
    
    # Save detailed results
    output_file = f"validation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump({
            'test_date': datetime.now().isoformat(),
            'parameters': {
                'start_balance': start_balance,
                'iterations': iterations,
                'trials_per_config': trials_per_config,
            },
            'results': all_results,
            'summary': config_summaries,
        }, f, indent=2)
    
    print(f"\nDetailed results saved to: {output_file}")
    
    # Recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    
    if best['min_edge'] <= 0.03:
        print("  ⚠ Lower edge threshold increases bet frequency but may reduce quality")
    elif best['min_edge'] >= 0.08:
        print("  ⚠ Higher edge threshold improves quality but reduces bet frequency")
    else:
        print("  ✓ Current edge threshold (0.05) is well-balanced")
    
    if best['kelly_factor'] <= 0.25:
        print("  → Very conservative betting (0.25x Kelly) reduces variance but also returns")
    elif best['kelly_factor'] >= 0.75:
        print("  → Aggressive betting (0.75x+ Kelly) maximizes returns but increases variance")
    else:
        print("  ✓ Half Kelly (0.5x) provides good balance of growth and risk management")
    
    current_kelly = config['bot'].get('kelly_factor', 0.25)
    print(f"\n  Current config: min_edge={config['bot']['min_edge']}, kelly_factor={current_kelly}")
    if best['min_edge'] != config['bot']['min_edge'] or best['kelly_factor'] != current_kelly:
        print(f"  Suggested: min_edge={best['min_edge']}, kelly_factor={best['kelly_factor']}")
        print(f"  Expected improvement: {best['avg_roi'] - 240:.1f}% ROI increase")


if __name__ == '__main__':
    main()
