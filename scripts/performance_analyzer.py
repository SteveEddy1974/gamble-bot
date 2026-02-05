#!/usr/bin/env python3
"""
Performance analysis tool for bot results.

Calculates:
- Sharpe ratio (risk-adjusted returns)
- Sortino ratio (downside risk)
- Maximum drawdown
- Win rate and average win/loss
- Profit factor
- Expected value per bet
- Volatility metrics
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
import math
from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Any


def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.0) -> float:
    """Calculate Sharpe ratio from returns."""
    if not returns or len(returns) < 2:
        return 0.0
    
    avg_return = sum(returns) / len(returns)
    variance = sum((r - avg_return) ** 2 for r in returns) / (len(returns) - 1)
    std_dev = math.sqrt(variance)
    
    if std_dev == 0:
        return 0.0
    
    return (avg_return - risk_free_rate) / std_dev


def calculate_sortino_ratio(returns: List[float], risk_free_rate: float = 0.0) -> float:
    """Calculate Sortino ratio (only considers downside volatility)."""
    if not returns or len(returns) < 2:
        return 0.0
    
    avg_return = sum(returns) / len(returns)
    downside_returns = [r for r in returns if r < risk_free_rate]
    
    if not downside_returns:
        return float('inf')
    
    downside_variance = sum((r - risk_free_rate) ** 2 for r in downside_returns) / len(downside_returns)
    downside_dev = math.sqrt(downside_variance)
    
    if downside_dev == 0:
        return float('inf')
    
    return (avg_return - risk_free_rate) / downside_dev


def calculate_max_drawdown(balance_history: List[float]) -> Dict[str, float]:
    """Calculate maximum drawdown and recovery info."""
    if not balance_history or len(balance_history) < 2:
        return {'max_drawdown': 0.0, 'max_drawdown_pct': 0.0, 'recovery_time': 0}
    
    peak = balance_history[0]
    max_dd = 0.0
    max_dd_pct = 0.0
    peak_idx = 0
    trough_idx = 0
    recovery_idx = 0
    
    for i, balance in enumerate(balance_history):
        if balance > peak:
            peak = balance
            peak_idx = i
            
        dd = peak - balance
        dd_pct = (dd / peak * 100) if peak > 0 else 0
        
        if dd > max_dd:
            max_dd = dd
            max_dd_pct = dd_pct
            trough_idx = i
            recovery_idx = None
        
        # Check if recovered from max drawdown
        if recovery_idx is None and balance >= peak and trough_idx > peak_idx:
            recovery_idx = i
    
    recovery_time = (recovery_idx - trough_idx) if recovery_idx else len(balance_history) - trough_idx
    
    return {
        'max_drawdown': max_dd,
        'max_drawdown_pct': max_dd_pct,
        'recovery_time': recovery_time,
        'peak_idx': peak_idx,
        'trough_idx': trough_idx,
    }


def analyze_trade_history(trade_history: List[Dict]) -> Dict[str, Any]:
    """Analyze individual trade results."""
    if not trade_history:
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'profit_factor': 0.0,
            'expected_value': 0.0,
        }
    
    wins = [t['profit'] for t in trade_history if t['profit'] > 0]
    losses = [t['profit'] for t in trade_history if t['profit'] <= 0]
    
    total_wins = sum(wins)
    total_losses = abs(sum(losses))
    
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0
    
    profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
    expected_value = sum(t['profit'] for t in trade_history) / len(trade_history)
    
    return {
        'total_trades': len(trade_history),
        'winning_trades': len(wins),
        'losing_trades': len(losses),
        'win_rate': len(wins) / len(trade_history) * 100,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'largest_win': max(wins) if wins else 0.0,
        'largest_loss': min(losses) if losses else 0.0,
        'profit_factor': profit_factor,
        'expected_value': expected_value,
        'total_profit': sum(t['profit'] for t in trade_history),
    }


def analyze_results_file(filepath: str):
    """Analyze a saved results JSON file."""
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    print("=" * 80)
    print(f"PERFORMANCE ANALYSIS: {filepath}")
    print("=" * 80)
    
    if 'test_date' in data:
        print(f"\nTest Date: {data['test_date']}")
    
    if 'parameters' in data:
        params = data['parameters']
        print(f"\nTest Parameters:")
        for key, value in params.items():
            print(f"  {key}: {value}")
    
    results = data.get('results', [])
    if not results:
        print("\nNo results found in file.")
        return
    
    print(f"\n{'=' * 80}")
    print("AGGREGATE STATISTICS")
    print("=" * 80)
    
    # Calculate returns
    rois = [r['roi'] for r in results]
    avg_roi = sum(rois) / len(rois)
    std_roi = math.sqrt(sum((r - avg_roi) ** 2 for r in rois) / len(rois))
    min_roi = min(rois)
    max_roi = max(rois)
    
    print(f"\nReturn Metrics:")
    print(f"  Average ROI: {avg_roi:+.2f}%")
    print(f"  Std Dev: {std_roi:.2f}%")
    print(f"  Min ROI: {min_roi:+.2f}%")
    print(f"  Max ROI: {max_roi:+.2f}%")
    print(f"  Coefficient of Variation: {(std_roi / abs(avg_roi) * 100):.1f}%")
    
    # Calculate Sharpe and Sortino
    sharpe = calculate_sharpe_ratio(rois)
    sortino = calculate_sortino_ratio(rois)
    
    print(f"\nRisk-Adjusted Metrics:")
    print(f"  Sharpe Ratio: {sharpe:.2f}")
    print(f"  Sortino Ratio: {sortino:.2f}")
    
    # Drawdown analysis
    drawdowns = [r['drawdown'] for r in results if 'drawdown' in r]
    if drawdowns:
        avg_dd = sum(drawdowns) / len(drawdowns)
        max_dd = min(drawdowns)
        print(f"\nDrawdown Metrics:")
        print(f"  Average Drawdown: {avg_dd:.2f}%")
        print(f"  Maximum Drawdown: {max_dd:.2f}%")
    
    # Betting statistics
    total_bets = sum(r['bets_placed'] for r in results)
    avg_bets = total_bets / len(results)
    
    print(f"\nBetting Statistics:")
    print(f"  Total Bets Placed: {total_bets:,}")
    print(f"  Average Bets per Trial: {avg_bets:.0f}")
    
    if 'avg_edge' in results[0]:
        edges = [r['avg_edge'] for r in results if r['avg_edge'] > 0]
        if edges:
            avg_edge = sum(edges) / len(edges)
            print(f"  Average Edge: {avg_edge:.3f} ({avg_edge*100:.1f}%)")
    
    # Success metrics
    profitable_trials = sum(1 for r in results if r['roi'] > 0)
    success_rate = profitable_trials / len(results) * 100
    
    print(f"\nSuccess Metrics:")
    print(f"  Profitable Trials: {profitable_trials}/{len(results)} ({success_rate:.1f}%)")
    
    # Configuration comparison (if multiple configs)
    if 'summary' in data:
        print(f"\n{'=' * 80}")
        print("CONFIGURATION COMPARISON")
        print("=" * 80)
        
        summaries = data['summary']
        print(f"\n{'Config':<25} {'Avg ROI':<12} {'Sharpe':<10} {'Avg Bets':<10}")
        print("-" * 80)
        
        for s in summaries[:5]:  # Top 5
            config_name = f"Edge={s['min_edge']:.2f}, K={s['kelly_factor']:.2f}x"
            print(f"{config_name:<25} {s['avg_roi']:+10.1f}% {sharpe:>8.2f} {s['avg_bets']:>9.0f}")
    
    print(f"\n{'=' * 80}")
    print("PERFORMANCE RATING")
    print("=" * 80)
    
    # Overall performance rating
    rating_points = 0
    max_points = 5
    
    if avg_roi > 100:
        rating_points += 1
        print("  ✓ Strong returns (>100% ROI)")
    if sharpe > 2.0:
        rating_points += 1
        print("  ✓ Excellent risk-adjusted returns (Sharpe > 2.0)")
    if success_rate >= 95:
        rating_points += 1
        print("  ✓ Very high consistency (95%+ profitable)")
    if std_roi < 30:
        rating_points += 1
        print("  ✓ Low volatility (std dev < 30%)")
    if drawdowns and max_dd > -20:
        rating_points += 1
        print("  ✓ Controlled drawdowns (< 20%)")
    
    rating = "★" * rating_points + "☆" * (max_points - rating_points)
    print(f"\n  Overall Rating: {rating} ({rating_points}/{max_points})")
    
    if rating_points >= 4:
        print("  → Excellent performance, ready for production")
    elif rating_points >= 3:
        print("  → Good performance, consider minor optimizations")
    else:
        print("  → Review configuration and risk parameters")


def main():
    print("=" * 80)
    print("PERFORMANCE ANALYZER")
    print("=" * 80)
    
    # Look for results files
    import glob
    result_files = glob.glob("validation_results_*.json")
    
    if not result_files:
        print("\nNo validation results files found.")
        print("Run extended_validation.py first to generate test results.")
        return
    
    # Use most recent file
    result_files.sort()
    latest_file = result_files[-1]
    
    print(f"\nFound {len(result_files)} result file(s)")
    print(f"Analyzing: {latest_file}\n")
    
    analyze_results_file(latest_file)
    
    # Offer to analyze all files
    if len(result_files) > 1:
        print(f"\n{'=' * 80}")
        response = input(f"\nAnalyze all {len(result_files)} files? (y/n): ")
        if response.lower() == 'y':
            for i, filepath in enumerate(result_files[:-1], 1):  # Skip last (already analyzed)
                print(f"\n\n{'=' * 80}")
                print(f"FILE {i+1}/{len(result_files)}")
                analyze_results_file(filepath)


if __name__ == '__main__':
    main()
