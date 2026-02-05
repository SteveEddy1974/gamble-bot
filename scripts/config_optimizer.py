#!/usr/bin/env python3
"""
Configuration optimizer - finds optimal bot parameters.

Tests different combinations of:
- max_stake_pct (2%, 3%, 5%)
- max_exposure_pct (8%, 10%, 15%)
- min_edge thresholds
- Kelly factors
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import load_config, BetManager, parse_shoe_state, parse_market_selections
from main import prob_natural_win, prob_pocket_pair, evaluate, size_stake, Opportunity
from api_client import SimulatedAPIClient
import time
import random
from itertools import product
import json
from datetime import datetime


def test_configuration(config_params: dict, iterations: int = 5000) -> dict:
    """Test a specific configuration."""
    start_balance = 1000
    max_exposure = start_balance * config_params['max_exposure_pct']
    bet_manager = BetManager(balance=start_balance, max_exposure=max_exposure)
    
    api_client = SimulatedAPIClient(
        start_cards_remaining=416,
        decrement=4,
        reset_after=80,
        settle_delay=1
    )
    
    bets_placed = 0
    min_balance = start_balance
    max_balance = start_balance
    
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
            if ok and edge >= config_params['min_edge']:
                stake = size_stake(
                    bet_manager.balance,
                    config_params['max_exposure_pct'],
                    edge,
                    price=sel.best_back_price,
                    true_prob=prob,
                    shrink=config_params.get('kelly_factor', 0.25),
                    max_stake_pct=config_params['max_stake_pct'],
                )
                
                if bet_manager.can_place(stake):
                    opp = Opportunity(sel, prob, sel.best_back_price, edge, 'BACK', stake)
                    bet_id = str(bets_placed + 1)
                    
                    bet_manager.record_accepted(bet_id, opp)
                    bets_placed += 1
                    
                    won = random.random() < prob
                    
                    if won:
                        payout = stake * (sel.best_back_price - 1.0)
                        bet_manager.process_settlement(bet_id, 'WON', payout)
                    else:
                        bet_manager.process_settlement(bet_id, 'LOST', 0.0)
                    
                    min_balance = min(min_balance, bet_manager.balance)
                    max_balance = max(max_balance, bet_manager.balance)
    
    final_balance = bet_manager.balance
    roi = ((final_balance - start_balance) / start_balance) * 100
    drawdown = ((min_balance - start_balance) / start_balance) * 100
    
    return {
        'final_balance': final_balance,
        'roi': roi,
        'bets_placed': bets_placed,
        'drawdown': drawdown,
        'min_balance': min_balance,
        'max_balance': max_balance,
    }


def main():
    print("=" * 80)
    print("CONFIGURATION OPTIMIZER")
    print("=" * 80)
    
    # Parameter space to test
    max_stake_pcts = [0.02, 0.03, 0.05]
    max_exposure_pcts = [0.08, 0.10, 0.15]
    min_edges = [0.03, 0.05, 0.08]
    kelly_factors = [0.25]  # Optimal quarter Kelly from validation
    
    iterations = 5000
    trials_per_config = 3
    
    print(f"\nTest Parameters:")
    print(f"  Iterations per trial: {iterations:,}")
    print(f"  Trials per configuration: {trials_per_config}")
    print(f"  Max stake %: {max_stake_pcts}")
    print(f"  Max exposure %: {max_exposure_pcts}")
    print(f"  Min edge: {min_edges}")
    print(f"  Kelly factor: {kelly_factors}")
    
    total_tests = len(max_stake_pcts) * len(max_exposure_pcts) * len(min_edges) * trials_per_config
    print(f"\nTotal tests: {total_tests}")
    print(f"Estimated time: ~{total_tests * 1.5:.0f} minutes\n")
    
    all_results = []
    test_num = 0
    
    # Test all combinations
    for max_stake_pct in max_stake_pcts:
        for max_exposure_pct in max_exposure_pcts:
            for min_edge in min_edges:
                for kelly_factor in kelly_factors:
                    config_params = {
                        'max_stake_pct': max_stake_pct,
                        'max_exposure_pct': max_exposure_pct,
                        'min_edge': min_edge,
                        'kelly_factor': kelly_factor,
                    }
                    
                    print(f"\nTesting: stake={max_stake_pct*100:.0f}%, exposure={max_exposure_pct*100:.0f}%, edge={min_edge:.2f}")
                    print("-" * 80)
                    
                    trial_results = []
                    
                    for trial in range(trials_per_config):
                        test_num += 1
                        print(f"  [{test_num}/{total_tests}] Trial {trial+1}/{trials_per_config}... ", end='', flush=True)
                        
                        start_time = time.time()
                        result = test_configuration(config_params, iterations)
                        elapsed = time.time() - start_time
                        
                        result.update(config_params)
                        result['trial'] = trial + 1
                        result['elapsed'] = elapsed
                        
                        trial_results.append(result)
                        all_results.append(result)
                        
                        print(f"ROI: {result['roi']:+.1f}%, Bets: {result['bets_placed']} ({elapsed:.1f}s)")
                    
                    # Summary for this config
                    avg_roi = sum(r['roi'] for r in trial_results) / len(trial_results)
                    avg_bets = sum(r['bets_placed'] for r in trial_results) / len(trial_results)
                    avg_dd = sum(r['drawdown'] for r in trial_results) / len(trial_results)
                    
                    print(f"  → Average: ROI {avg_roi:+.1f}%, {avg_bets:.0f} bets, {avg_dd:.1f}% DD")
    
    # Analysis
    print("\n" + "=" * 80)
    print("OPTIMIZATION RESULTS")
    print("=" * 80)
    
    # Group by configuration
    from collections import defaultdict
    by_config = defaultdict(list)
    
    for r in all_results:
        key = (r['max_stake_pct'], r['max_exposure_pct'], r['min_edge'])
        by_config[key].append(r)
    
    # Calculate summaries
    summaries = []
    for (stake, exposure, edge), results in by_config.items():
        avg_roi = sum(r['roi'] for r in results) / len(results)
        std_roi = (sum((r['roi'] - avg_roi) ** 2 for r in results) / len(results)) ** 0.5
        avg_bets = sum(r['bets_placed'] for r in results) / len(results)
        avg_dd = sum(r['drawdown'] for r in results) / len(results)
        
        # Risk-adjusted score (Sharpe-like)
        risk_adjusted_roi = avg_roi / std_roi if std_roi > 0 else 0
        
        summaries.append({
            'max_stake_pct': stake,
            'max_exposure_pct': exposure,
            'min_edge': edge,
            'avg_roi': avg_roi,
            'std_roi': std_roi,
            'avg_bets': avg_bets,
            'avg_drawdown': avg_dd,
            'risk_adjusted_roi': risk_adjusted_roi,
        })
    
    # Sort by risk-adjusted ROI
    summaries.sort(key=lambda x: x['risk_adjusted_roi'], reverse=True)
    
    print("\nTop 10 Configurations (by risk-adjusted ROI):")
    print("-" * 80)
    print(f"{'Stake%':<8} {'Exp%':<8} {'Edge':<8} {'Avg ROI':<12} {'Std':<8} {'Bets':<8} {'DD%':<8} {'Score':<8}")
    print("-" * 80)
    
    for i, s in enumerate(summaries[:10], 1):
        marker = "★" if i == 1 else " "
        print(f"{marker} {s['max_stake_pct']*100:>5.0f}% {s['max_exposure_pct']*100:>6.0f}% "
              f"{s['min_edge']:>6.2f} {s['avg_roi']:>10.1f}% {s['std_roi']:>6.1f}% "
              f"{s['avg_bets']:>6.0f} {s['avg_drawdown']:>6.1f}% {s['risk_adjusted_roi']:>6.2f}")
    
    # Best configuration
    best = summaries[0]
    print("\n" + "=" * 80)
    print("OPTIMAL CONFIGURATION")
    print("=" * 80)
    print(f"  Max Stake:        {best['max_stake_pct']*100:.0f}%")
    print(f"  Max Exposure:     {best['max_exposure_pct']*100:.0f}%")
    print(f"  Min Edge:         {best['min_edge']:.2f}")
    print(f"  Average ROI:      {best['avg_roi']:+.1f}%")
    print(f"  ROI Volatility:   {best['std_roi']:.1f}%")
    print(f"  Average Bets:     {best['avg_bets']:.0f}")
    print(f"  Average Drawdown: {best['avg_drawdown']:.1f}%")
    print(f"  Risk-Adj Score:   {best['risk_adjusted_roi']:.2f}")
    
    # Save results
    output_file = f"optimizer_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump({
            'test_date': datetime.now().isoformat(),
            'parameters': {
                'iterations': iterations,
                'trials_per_config': trials_per_config,
            },
            'results': all_results,
            'summaries': summaries,
            'optimal': best,
        }, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")
    
    # Recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    
    current_config = load_config()
    current_stake = current_config['bot'].get('max_stake_pct', 0.03)
    current_exposure = current_config['bot']['max_exposure_pct']
    current_edge = current_config['bot']['min_edge']
    
    print(f"\nCurrent config: stake={current_stake*100:.0f}%, exposure={current_exposure*100:.0f}%, edge={current_edge:.2f}")
    print(f"Optimal config: stake={best['max_stake_pct']*100:.0f}%, exposure={best['max_exposure_pct']*100:.0f}%, edge={best['min_edge']:.2f}")
    
    if (best['max_stake_pct'] != current_stake or 
        best['max_exposure_pct'] != current_exposure or 
        best['min_edge'] != current_edge):
        print(f"\n✓ Update config.yaml with optimal parameters for better performance")
        print(f"  Expected improvement: {best['avg_roi'] - 240:.1f}% ROI")
    else:
        print(f"\n✓ Current configuration is already optimal!")


if __name__ == '__main__':
    main()
