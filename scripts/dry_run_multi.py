#!/usr/bin/env python3
"""Multi-run dry simulation to evaluate average profitability over N trials.

Usage: python scripts/dry_run_multi.py [iterations_per_run] [num_runs]
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from scripts.dry_run import run_dry


def run_multi(iterations=1000, num_runs=10, start_balance=1000, max_exposure_pct=0.1):
    """Run multiple independent simulations and aggregate results."""
    results = []
    
    for run_num in range(num_runs):
        print(f"\nRun {run_num + 1}/{num_runs}:")
        bm, stats = run_dry(iterations, start_balance, max_exposure_pct)
        results.append({
            'run': run_num + 1,
            'final_balance': bm.balance,
            'pnl': bm.pnl,
            'placed': stats['placed'],
            'accepted': stats['accepted'],
            'wins': stats['settled_won'],
            'losses': stats['settled_lost']
        })
        
        print(f"  Placed: {stats['placed']}, Wins: {stats['settled_won']}, Losses: {stats['settled_lost']}")
        print(f"  Final Balance: {bm.balance:.2f}, PnL: {bm.pnl:+.2f}")
    
    # Aggregate statistics
    avg_pnl = sum(r['pnl'] for r in results) / num_runs
    avg_balance = sum(r['final_balance'] for r in results) / num_runs
    avg_placed = sum(r['placed'] for r in results) / num_runs
    total_wins = sum(r['wins'] for r in results)
    total_losses = sum(r['losses'] for r in results)
    win_rate = total_wins / (total_wins + total_losses) if (total_wins + total_losses) > 0 else 0
    
    profitable_runs = sum(1 for r in results if r['pnl'] > 0)
    
    print(f"\n{'='*60}")
    print(f"AGGREGATE RESULTS ({num_runs} runs x {iterations} iterations)")
    print(f"{'='*60}")
    print(f"Average Final Balance: ${avg_balance:.2f}")
    print(f"Average PnL: ${avg_pnl:+.2f} ({avg_pnl/start_balance*100:+.1f}%)")
    print(f"Average Bets Placed: {avg_placed:.1f}")
    print(f"Total Wins/Losses: {total_wins}/{total_losses}")
    print(f"Win Rate: {win_rate*100:.1f}%")
    print(f"Profitable Runs: {profitable_runs}/{num_runs} ({profitable_runs/num_runs*100:.0f}%)")
    print(f"{'='*60}")
    
    return results


if __name__ == '__main__':
    iters = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    runs = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    run_multi(iters, runs)
