#!/usr/bin/env python3
"""
Test bot strategy with different parameters to find optimal settings.

This script runs multiple simulations with varying:
- min_edge thresholds
- max_exposure percentages
- Different shoe scenarios

Results help optimize the bot for real trading.
"""
import pytest
pytest.skip("Strategy optimization tests are disabled in automated runs (long-running and optimization-related).", allow_module_level=True)
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import load_config, main as run_bot
import yaml
import time
from io import StringIO
import logging


def test_parameter_grid():
    """Test different parameter combinations."""
    print("=" * 80)
    print("STRATEGY PARAMETER GRID SEARCH")
    print("=" * 80)
    print()
    
    # Parameter ranges to test
    min_edge_values = [0.03, 0.05, 0.07, 0.10]
    max_exposure_values = [0.05, 0.10, 0.15, 0.20]
    
    start_balance = 1000
    iterations = 2000  # Reasonable for each combo
    
    results = []
    
    total_tests = len(min_edge_values) * len(max_exposure_values)
    test_num = 0
    
    print(f"Testing {total_tests} parameter combinations...")
    print(f"Each test: {iterations} iterations, starting balance: £{start_balance}")
    print()
    
    for min_edge in min_edge_values:
        for max_exposure in max_exposure_values:
            test_num += 1
            print(f"Test {test_num}/{total_tests}: min_edge={min_edge:.2%}, max_exposure={max_exposure:.2%}")
            
            start_time = time.time()
            
            # Run simulation
            final_balance, bets_placed, opportunities_found, win_count = simulate_session(
                iterations=iterations,
                start_balance=start_balance,
                min_edge=min_edge,
                max_exposure_pct=max_exposure
            )
            
            elapsed = time.time() - start_time
            
            # Calculate metrics
            profit = final_balance - start_balance
            roi = (profit / start_balance) * 100
            win_rate = (win_count / bets_placed * 100) if bets_placed > 0 else 0
            
            result = {
                'min_edge': min_edge,
                'max_exposure': max_exposure,
                'final_balance': final_balance,
                'profit': profit,
                'roi': roi,
                'bets_placed': bets_placed,
                'opportunities_found': opportunities_found,
                'win_count': win_count,
                'win_rate': win_rate,
                'elapsed': elapsed
            }
            
            results.append(result)
            
            print(f"  Result: £{final_balance:.2f} ({roi:+.1f}%), "
                  f"{bets_placed} bets, {win_rate:.1f}% win rate, "
                  f"{elapsed:.1f}s")
            print()
    
    # Analyze results
    print()
    print("=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    print()
    
    # Sort by ROI
    results_by_roi = sorted(results, key=lambda x: x['roi'], reverse=True)
    
    print("Top 5 by ROI:")
    print(f"{'Rank':<6} {'Edge':<8} {'Exposure':<10} {'ROI':<10} {'Bets':<8} {'Win%':<8} {'Final':<12}")
    print("-" * 80)
    
    for i, r in enumerate(results_by_roi[:5], 1):
        print(f"{i:<6} {r['min_edge']:.2%:<8} {r['max_exposure']:.2%:<10} "
              f"{r['roi']:+.1f}%{'':<5} {r['bets_placed']:<8} {r['win_rate']:.1f}%{'':<5} "
              f"£{r['final_balance']:.2f}")
    
    print()
    print("Bottom 5 by ROI:")
    print(f"{'Rank':<6} {'Edge':<8} {'Exposure':<10} {'ROI':<10} {'Bets':<8} {'Win%':<8} {'Final':<12}")
    print("-" * 80)
    
    for i, r in enumerate(results_by_roi[-5:], 1):
        print(f"{i:<6} {r['min_edge']:.2%:<8} {r['max_exposure']:.2%:<10} "
              f"{r['roi']:+.1f}%{'':<5} {r['bets_placed']:<8} {r['win_rate']:.1f}%{'':<5} "
              f"£{r['final_balance']:.2f}")
    
    print()
    
    # Best overall
    best = results_by_roi[0]
    print("=" * 80)
    print("OPTIMAL PARAMETERS FOUND")
    print("=" * 80)
    print()
    print(f"Min Edge:        {best['min_edge']:.2%}")
    print(f"Max Exposure:    {best['max_exposure']:.2%}")
    print(f"ROI:             {best['roi']:+.1f}%")
    print(f"Final Balance:   £{best['final_balance']:.2f}")
    print(f"Bets Placed:     {best['bets_placed']}")
    print(f"Win Rate:        {best['win_rate']:.1f}%")
    print(f"Opportunities:   {best['opportunities_found']}")
    print()
    
    # Save to file
    with open('parameter_test_results.csv', 'w') as f:
        f.write('min_edge,max_exposure,roi,profit,final_balance,bets_placed,win_rate,opportunities\n')
        for r in results_by_roi:
            f.write(f"{r['min_edge']},{r['max_exposure']},{r['roi']:.2f},"
                   f"{r['profit']:.2f},{r['final_balance']:.2f},"
                   f"{r['bets_placed']},{r['win_rate']:.2f},{r['opportunities_found']}\n")
    
    print("Results saved to: parameter_test_results.csv")
    print()


def test_edge_threshold_sensitivity():
    """Test how ROI changes with edge threshold."""
    print("=" * 80)
    print("EDGE THRESHOLD SENSITIVITY ANALYSIS")
    print("=" * 80)
    print()
    
    edge_thresholds = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 0.12, 0.15]
    
    start_balance = 1000
    iterations = 2000
    max_exposure = 0.10
    
    print(f"Testing {len(edge_thresholds)} edge thresholds")
    print(f"Fixed: max_exposure={max_exposure:.2%}, iterations={iterations}")
    print()
    
    results = []
    
    for edge in edge_thresholds:
        print(f"Testing min_edge={edge:.2%}...", end=' ', flush=True)
        
        final_balance, bets_placed, opportunities_found, win_count = simulate_session(
            iterations=iterations,
            start_balance=start_balance,
            min_edge=edge,
            max_exposure_pct=max_exposure
        )
        
        profit = final_balance - start_balance
        roi = (profit / start_balance) * 100
        win_rate = (win_count / bets_placed * 100) if bets_placed > 0 else 0
        
        results.append({
            'edge': edge,
            'roi': roi,
            'bets': bets_placed,
            'win_rate': win_rate,
            'opportunities': opportunities_found
        })
        
        print(f"ROI: {roi:+.1f}%, Bets: {bets_placed}, Win%: {win_rate:.1f}")
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print(f"{'Edge Threshold':<16} {'ROI':<12} {'Bets':<10} {'Win%':<10} {'Opps':<10}")
    print("-" * 80)
    
    for r in results:
        print(f"{r['edge']:.2%:<16} {r['roi']:+.1f}%{'':<7} {r['bets']:<10} "
              f"{r['win_rate']:.1f}%{'':<6} {r['opportunities']:<10}")
    
    print()
    print("Key Observations:")
    print(f"- Lower edge threshold = More bets but potentially lower win rate")
    print(f"- Higher edge threshold = Fewer bets but potentially higher win rate")
    print(f"- Optimal edge appears to be around: {max(results, key=lambda x: x['roi'])['edge']:.2%}")
    print()


def test_long_term_stability():
    """Test bot performance over extended runs."""
    print("=" * 80)
    print("LONG-TERM STABILITY TEST")
    print("=" * 80)
    print()
    
    runs = 5
    iterations = 10000
    start_balance = 1000
    min_edge = 0.05
    max_exposure = 0.10
    
    print(f"Running {runs} independent sessions")
    print(f"Each session: {iterations} iterations")
    print(f"Parameters: min_edge={min_edge:.2%}, max_exposure={max_exposure:.2%}")
    print()
    
    results = []
    
    for run_num in range(1, runs + 1):
        print(f"Run {run_num}/{runs}...", end=' ', flush=True)
        
        start_time = time.time()
        
        final_balance, bets_placed, opportunities_found, win_count = simulate_session(
            iterations=iterations,
            start_balance=start_balance,
            min_edge=min_edge,
            max_exposure_pct=max_exposure
        )
        
        elapsed = time.time() - start_time
        
        profit = final_balance - start_balance
        roi = (profit / start_balance) * 100
        win_rate = (win_count / bets_placed * 100) if bets_placed > 0 else 0
        
        results.append({
            'run': run_num,
            'roi': roi,
            'final': final_balance,
            'bets': bets_placed,
            'win_rate': win_rate
        })
        
        print(f"£{final_balance:.2f} ({roi:+.1f}%), {elapsed:.1f}s")
    
    print()
    print("=" * 80)
    print("STABILITY ANALYSIS")
    print("=" * 80)
    print()
    
    avg_roi = sum(r['roi'] for r in results) / len(results)
    min_roi = min(r['roi'] for r in results)
    max_roi = max(r['roi'] for r in results)
    
    profitable_runs = sum(1 for r in results if r['roi'] > 0)
    
    print(f"Average ROI:      {avg_roi:+.1f}%")
    print(f"Min ROI:          {min_roi:+.1f}%")
    print(f"Max ROI:          {max_roi:+.1f}%")
    print(f"Profitable Runs:  {profitable_runs}/{runs} ({profitable_runs/runs*100:.0f}%)")
    print()
    
    print("Individual Run Results:")
    print(f"{'Run':<6} {'ROI':<12} {'Final Balance':<16} {'Bets':<10} {'Win%':<10}")
    print("-" * 80)
    
    for r in results:
        print(f"{r['run']:<6} {r['roi']:+.1f}%{'':<7} £{r['final']:<14.2f} "
              f"{r['bets']:<10} {r['win_rate']:.1f}%")
    
    print()
    
    if profitable_runs == runs:
        print("✓ EXCELLENT: 100% profitable runs - strategy is highly consistent")
    elif profitable_runs >= runs * 0.8:
        print("✓ GOOD: 80%+ profitable runs - strategy is reliable")
    elif profitable_runs >= runs * 0.6:
        print("⚠ MODERATE: 60-80% profitable runs - strategy has variance")
    else:
        print("✗ CONCERN: <60% profitable runs - review strategy")
    
    print()


def test_extreme_scenarios():
    """Test bot in extreme edge cases."""
    print("=" * 80)
    print("EXTREME SCENARIO TESTING")
    print("=" * 80)
    print()
    
    scenarios = [
        {
            'name': 'Conservative (high edge, low exposure)',
            'min_edge': 0.15,
            'max_exposure': 0.05
        },
        {
            'name': 'Aggressive (low edge, high exposure)',
            'min_edge': 0.02,
            'max_exposure': 0.20
        },
        {
            'name': 'Balanced (current settings)',
            'min_edge': 0.05,
            'max_exposure': 0.10
        },
        {
            'name': 'Very Conservative (very high edge, very low exposure)',
            'min_edge': 0.20,
            'max_exposure': 0.03
        },
    ]
    
    start_balance = 1000
    iterations = 2000
    
    for scenario in scenarios:
        print(f"Testing: {scenario['name']}")
        print(f"  min_edge={scenario['min_edge']:.2%}, max_exposure={scenario['max_exposure']:.2%}")
        
        final_balance, bets_placed, opportunities_found, win_count = simulate_session(
            iterations=iterations,
            start_balance=start_balance,
            min_edge=scenario['min_edge'],
            max_exposure_pct=scenario['max_exposure']
        )
        
        profit = final_balance - start_balance
        roi = (profit / start_balance) * 100
        win_rate = (win_count / bets_placed * 100) if bets_placed > 0 else 0
        
        print(f"  Result: £{final_balance:.2f} ({roi:+.1f}%)")
        print(f"  Bets: {bets_placed}, Win Rate: {win_rate:.1f}%")
        print()


def main():
    """Run all tests."""
    print()
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "STRATEGY OPTIMIZATION TEST SUITE" + " " * 26 + "║")
    print("╚" + "═" * 78 + "╝")
    print()
    
    choice = input("""
Select test to run:

1. Parameter Grid Search (comprehensive, ~30 minutes)
2. Edge Threshold Sensitivity (quick, ~5 minutes)
3. Long-term Stability Test (moderate, ~15 minutes)
4. Extreme Scenarios (quick, ~3 minutes)
5. Run All Tests (comprehensive, ~1 hour)

Choice (1-5): """).strip()
    
    print()
    
    if choice == '1':
        test_parameter_grid()
    elif choice == '2':
        test_edge_threshold_sensitivity()
    elif choice == '3':
        test_long_term_stability()
    elif choice == '4':
        test_extreme_scenarios()
    elif choice == '5':
        print("Running all tests...")
        print()
        test_edge_threshold_sensitivity()
        input("\nPress Enter to continue to next test...")
        test_extreme_scenarios()
        input("\nPress Enter to continue to next test...")
        test_long_term_stability()
        input("\nPress Enter to continue to next test...")
        test_parameter_grid()
    else:
        print("Invalid choice. Exiting.")
        return
    
    print()
    print("=" * 80)
    print("TESTING COMPLETE")
    print("=" * 80)
    print()


if __name__ == '__main__':
    main()
