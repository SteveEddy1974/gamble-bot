#!/usr/bin/env python3
"""
Comprehensive bankroll testing to find minimum viable starting amount.

Tests multiple starting bankrolls with multiple trials each to understand:
- Risk of ruin at different bankroll sizes
- Impact of variance on small vs large bankrolls
- Minimum recommended starting amount
- Return consistency across bankroll sizes
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import load_config, BetManager, parse_shoe_state, parse_market_selections, prob_natural_win, prob_pocket_pair, evaluate, size_stake, Opportunity
from api_client import SimulatedAPIClient
import time
import logging
from collections import defaultdict
import random

logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors to keep output clean
    format='%(levelname)s: %(message)s'
)


def run_bankroll_test(start_balance, iterations, config):
    """Run a single test with given starting bankroll."""
    max_exposure = start_balance * config['bot']['max_exposure_pct']
    bet_manager = BetManager(
        balance=start_balance,
        max_exposure=max_exposure
    )
    
    # Create simulated API client
    api_client = SimulatedAPIClient(
        start_cards_remaining=config['bot']['simulate_start_cards'],
        decrement=config['bot']['simulate_decrement'],
        reset_after=config['bot'].get('simulate_reset_after')
    )
    
    min_edge = config['bot']['min_edge']
    bets_placed = 0
    opportunities_found = 0
    opportunities_skipped = 0
    min_balance = start_balance
    max_balance = start_balance
    
    for i in range(iterations):
        # Get market snapshot
        xml_root = api_client.get_snapshot(channel_id='123')
        
        # Parse shoe state and selections
        shoe_elem = xml_root.find('shoe')
        selections_elem = xml_root.find('marketSelections')
        shoe = parse_shoe_state(shoe_elem)
        selections = parse_market_selections(selections_elem)
        if shoe is None:
            continue
        
        # Check for opportunities
        for sel in selections:
            if sel.status != 'IN_PLAY':
                continue
            
            # Natural Win
            if sel.name == 'Natural Win' and sel.best_back_price:
                prob = prob_natural_win(shoe)
                ok, edge = evaluate(sel, prob, sel.best_back_price, 'BACK')
                if ok and edge >= min_edge:
                    opportunities_found += 1
                    stake = size_stake(
                        bet_manager.balance,
                        config['bot']['max_exposure_pct'],
                        edge,
                        price=sel.best_back_price,
                        true_prob=prob,
                        max_stake_pct=config['bot'].get('max_stake_pct', 0.03),
                    )
                    
                    if bet_manager.can_place(stake):
                        opp = Opportunity(sel, prob, sel.best_back_price, edge, 'BACK', stake)
                        bet_id = str(bets_placed + 1)
                        
                        # Simulate bet placement
                        bet_manager.record_accepted(bet_id, opp)
                        bets_placed += 1
                        
                        # Simulate immediate settlement
                        won = random.random() < prob
                        
                        if won:
                            payout = stake * (sel.best_back_price - 1.0)
                            profit = bet_manager.process_settlement(bet_id, 'WON', payout)
                        else:
                            profit = bet_manager.process_settlement(bet_id, 'LOST', 0.0)
                        
                        # Track min/max balance
                        min_balance = min(min_balance, bet_manager.balance)
                        max_balance = max(max_balance, bet_manager.balance)
                    else:
                        opportunities_skipped += 1
            
            # Pocket Pair
            if sel.name == 'Pocket Pair In Any Hand' and sel.best_back_price:
                prob = prob_pocket_pair(shoe)
                ok, edge = evaluate(sel, prob, sel.best_back_price, 'BACK')
                if ok and edge >= min_edge:
                    opportunities_found += 1
                    stake = size_stake(
                        bet_manager.balance,
                        config['bot']['max_exposure_pct'],
                        edge,
                        price=sel.best_back_price,
                        true_prob=prob,
                        max_stake_pct=config['bot'].get('max_stake_pct', 0.03),
                    )
                    
                    if bet_manager.can_place(stake):
                        opp = Opportunity(sel, prob, sel.best_back_price, edge, 'BACK', stake)
                        bet_id = str(bets_placed + 1)
                        
                        bet_manager.record_accepted(bet_id, opp)
                        bets_placed += 1
                        
                        won = random.random() < prob
                        
                        if won:
                            payout = stake * (sel.best_back_price - 1.0)
                            profit = bet_manager.process_settlement(bet_id, 'WON', payout)
                        else:
                            profit = bet_manager.process_settlement(bet_id, 'LOST', 0.0)
                        
                        min_balance = min(min_balance, bet_manager.balance)
                        max_balance = max(max_balance, bet_manager.balance)
                    else:
                        opportunities_skipped += 1
    
    final_balance = bet_manager.balance
    profit = final_balance - start_balance
    roi = (profit / start_balance) * 100
    max_drawdown = ((min_balance - start_balance) / start_balance) * 100
    max_growth = ((max_balance - start_balance) / start_balance) * 100
    
    return {
        'start_balance': start_balance,
        'final_balance': final_balance,
        'profit': profit,
        'roi': roi,
        'bets_placed': bets_placed,
        'opportunities_found': opportunities_found,
        'opportunities_skipped': opportunities_skipped,
        'min_balance': min_balance,
        'max_balance': max_balance,
        'max_drawdown': max_drawdown,
        'max_growth': max_growth,
        'busted': final_balance < (start_balance * 0.1)  # Lost 90%+ = busted
    }


def main():
    """Run comprehensive bankroll tests."""
    config = load_config()
    
    # Test parameters
    bankrolls = [10, 25, 50, 100, 200, 500, 1000]
    iterations = 1000  # Iterations per trial
    trials = 5  # Multiple trials per bankroll
    
    print("=" * 80)
    print("COMPREHENSIVE BANKROLL TESTING")
    print("=" * 80)
    print(f"\nTest Parameters:")
    print(f"  Iterations per trial: {iterations}")
    print(f"  Trials per bankroll: {trials}")
    print(f"  Min edge: {config['bot']['min_edge']}")
    print(f"  Max exposure: {config['bot']['max_exposure_pct'] * 100}%")
    print(f"  Max stake per bet: {config['bot'].get('max_stake_pct', 0.03) * 100}%")
    print()
    
    all_results = defaultdict(list)
    
    for bankroll in bankrolls:
        print(f"\nTesting £{bankroll} starting bankroll...")
        print("-" * 80)
        
        for trial in range(trials):
            print(f"  Trial {trial + 1}/{trials}...", end=' ', flush=True)
            
            result = run_bankroll_test(bankroll, iterations, config)
            all_results[bankroll].append(result)
            
            print(f"Final: £{result['final_balance']:.2f} ({result['roi']:+.1f}%) " +
                  f"{'💀 BUSTED' if result['busted'] else '✓'}")
    
    # Summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY RESULTS")
    print("=" * 80)
    print()
    print(f"{'Bankroll':<12} {'Avg ROI':<12} {'Bust Rate':<12} {'Avg Bets':<12} {'Avg Drawdown':<15}")
    print("-" * 80)
    
    for bankroll in bankrolls:
        results = all_results[bankroll]
        avg_roi = sum(r['roi'] for r in results) / len(results)
        bust_rate = sum(1 for r in results if r['busted']) / len(results) * 100
        avg_bets = sum(r['bets_placed'] for r in results) / len(results)
        avg_drawdown = sum(r['max_drawdown'] for r in results) / len(results)
        
        print(f"£{bankroll:<11} {avg_roi:+.1f}%{' ' * 7} {bust_rate:.0f}%{' ' * 9} " +
              f"{avg_bets:.0f}{' ' * 9} {avg_drawdown:.1f}%")
    
    print()
    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print()
    
    # Find minimum safe bankroll (0% bust rate)
    safe_bankrolls = [br for br in bankrolls 
                      if all(not r['busted'] for r in all_results[br])]
    
    if safe_bankrolls:
        min_safe = min(safe_bankrolls)
        print(f"✓ Minimum Safe Bankroll: £{min_safe}")
        print(f"  - 0% risk of ruin over {iterations} iterations")
        print(f"  - Average ROI: {sum(r['roi'] for r in all_results[min_safe]) / len(all_results[min_safe]):+.1f}%")
    else:
        print("⚠️  No bankroll achieved 0% bust rate - increase test iterations")
    
    # Find optimal bankroll (best risk-adjusted return)
    print()
    print(f"✓ Recommended Starting Bankrolls:")
    for bankroll in bankrolls:
        results = all_results[bankroll]
        bust_rate = sum(1 for r in results if r['busted']) / len(results) * 100
        avg_roi = sum(r['roi'] for r in results) / len(results)
        
        if bust_rate == 0 and avg_roi > 0:
            print(f"  - £{bankroll}: {avg_roi:+.1f}% ROI, 0% bust risk")
    
    print()
    print("Key Insights:")
    print("  - Smaller bankrolls face higher variance risk")
    print("  - Larger bankrolls allow more concurrent opportunities")
    print("  - 3% max stake helps protect against ruin")
    print("  - Edge manifests more consistently with 500+ iterations")
    print()


if __name__ == '__main__':
    main()
