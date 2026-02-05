#!/usr/bin/env python3
"""
Automated daily performance reporting system.

Generates comprehensive reports including:
- Daily P&L summary
- Win/loss statistics
- Edge analysis
- Risk metrics
- Performance trends
- Email/file output
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
from collections import defaultdict
import math


def generate_daily_report(date: datetime, data: Dict[str, Any]) -> str:
    """Generate formatted daily report."""
    report = []
    
    # Header
    report.append("=" * 80)
    report.append(f"BACCARAT BOT - DAILY PERFORMANCE REPORT")
    report.append(f"Date: {date.strftime('%A, %B %d, %Y')}")
    report.append("=" * 80)
    
    # Executive Summary
    report.append("\n📊 EXECUTIVE SUMMARY")
    report.append("-" * 80)
    report.append(f"  Daily P&L:        £{data['daily_pnl']:+,.2f} ({data['daily_roi']:+.2f}%)")
    report.append(f"  Total P&L:        £{data['total_pnl']:+,.2f}")
    report.append(f"  Current Balance:  £{data['current_balance']:,.2f}")
    report.append(f"  Total ROI:        {data['total_roi']:+.2f}%")
    
    # Trading Activity
    report.append("\n📈 TRADING ACTIVITY")
    report.append("-" * 80)
    report.append(f"  Bets Placed:      {data['bets_placed']}")
    report.append(f"  Winning Bets:     {data['winning_bets']} ({data['win_rate']:.1f}%)")
    report.append(f"  Losing Bets:      {data['losing_bets']}")
    report.append(f"  Average Stake:    £{data['avg_stake']:.2f}")
    report.append(f"  Largest Win:      £{data['largest_win']:+.2f}")
    report.append(f"  Largest Loss:     £{data['largest_loss']:+.2f}")
    
    # Edge Analysis
    report.append("\n🎯 EDGE ANALYSIS")
    report.append("-" * 80)
    report.append(f"  Opportunities:    {data['opportunities_found']}")
    report.append(f"  Bet Conversion:   {data['bet_conversion']:.1f}%")
    report.append(f"  Average Edge:     {data['avg_edge']:.3f} ({data['avg_edge']*100:.1f}%)")
    report.append(f"  Min Edge:         {data['min_edge']:.3f}")
    report.append(f"  Max Edge:         {data['max_edge']:.3f}")
    
    # Risk Metrics
    report.append("\n⚠️  RISK METRICS")
    report.append("-" * 80)
    report.append(f"  Current Drawdown: {data['current_drawdown']:.2f}%")
    report.append(f"  Max Drawdown:     {data['max_drawdown']:.2f}%")
    report.append(f"  Peak Balance:     £{data['peak_balance']:,.2f}")
    report.append(f"  Exposure Used:    {data['avg_exposure']:.1f}%")
    
    # Performance Trends
    if 'trend_7d' in data:
        report.append("\n📉 PERFORMANCE TRENDS")
        report.append("-" * 80)
        report.append(f"  7-Day Avg ROI:    {data['trend_7d']:+.2f}%")
        report.append(f"  30-Day Avg ROI:   {data['trend_30d']:+.2f}%")
        report.append(f"  7-Day Win Rate:   {data['winrate_7d']:.1f}%")
    
    # Market Breakdown
    if 'by_selection' in data:
        report.append("\n🎲 MARKET BREAKDOWN")
        report.append("-" * 80)
        for sel_name, stats in data['by_selection'].items():
            report.append(f"  {sel_name}:")
            report.append(f"    Bets: {stats['count']}, Win Rate: {stats['win_rate']:.1f}%, P&L: £{stats['pnl']:+.2f}")
    
    # System Health
    report.append("\n🔧 SYSTEM HEALTH")
    report.append("-" * 80)
    report.append(f"  API Uptime:       {data['api_uptime']:.2f}%")
    report.append(f"  Avg Response:     {data['avg_response_time']:.0f}ms")
    report.append(f"  Errors Today:     {data['errors_today']}")
    
    # Alerts & Warnings
    if data.get('alerts'):
        report.append("\n🚨 ALERTS & WARNINGS")
        report.append("-" * 80)
        for alert in data['alerts']:
            report.append(f"  [{alert['time']}] {alert['message']}")
    
    # Footer
    report.append("\n" + "=" * 80)
    report.append(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 80)
    
    return "\n".join(report)


def generate_weekly_summary(start_date: datetime, data: List[Dict]) -> str:
    """Generate weekly performance summary."""
    report = []
    
    report.append("=" * 80)
    report.append(f"WEEKLY PERFORMANCE SUMMARY")
    report.append(f"Week of {start_date.strftime('%B %d, %Y')}")
    report.append("=" * 80)
    
    # Aggregate weekly stats
    total_pnl = sum(d['daily_pnl'] for d in data)
    total_bets = sum(d['bets_placed'] for d in data)
    total_wins = sum(d['winning_bets'] for d in data)
    
    avg_daily_pnl = total_pnl / len(data)
    avg_daily_roi = sum(d['daily_roi'] for d in data) / len(data)
    weekly_win_rate = (total_wins / total_bets * 100) if total_bets > 0 else 0
    
    report.append("\n📊 WEEKLY HIGHLIGHTS")
    report.append("-" * 80)
    report.append(f"  Weekly P&L:       £{total_pnl:+,.2f}")
    report.append(f"  Avg Daily P&L:    £{avg_daily_pnl:+,.2f}")
    report.append(f"  Avg Daily ROI:    {avg_daily_roi:+.2f}%")
    report.append(f"  Total Bets:       {total_bets}")
    report.append(f"  Win Rate:         {weekly_win_rate:.1f}%")
    
    # Best/worst days
    best_day = max(data, key=lambda x: x['daily_pnl'])
    worst_day = min(data, key=lambda x: x['daily_pnl'])
    
    report.append("\n🏆 BEST/WORST DAYS")
    report.append("-" * 80)
    report.append(f"  Best Day:         £{best_day['daily_pnl']:+.2f} ({best_day['date']})")
    report.append(f"  Worst Day:        £{worst_day['daily_pnl']:+.2f} ({worst_day['date']})")
    
    # Daily breakdown
    report.append("\n📅 DAILY BREAKDOWN")
    report.append("-" * 80)
    report.append(f"{'Date':<12} {'P&L':>12} {'ROI':>8} {'Bets':>6} {'Win%':>6}")
    report.append("-" * 80)
    for d in data:
        report.append(f"{d['date']:<12} £{d['daily_pnl']:>10,.2f} {d['daily_roi']:>6.1f}% {d['bets_placed']:>6} {d['win_rate']:>5.1f}%")
    
    report.append("\n" + "=" * 80)
    
    return "\n".join(report)


def save_report(report: str, filename: str):
    """Save report to file."""
    reports_dir = 'reports'
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)
    
    filepath = os.path.join(reports_dir, filename)
    with open(filepath, 'w') as f:
        f.write(report)
    
    return filepath


def generate_sample_report():
    """Generate sample report for demonstration."""
    import random
    
    date = datetime.now()
    
    # Sample data
    data = {
        'daily_pnl': random.uniform(50, 150),
        'daily_roi': random.uniform(5, 15),
        'total_pnl': random.uniform(500, 2000),
        'current_balance': random.uniform(1200, 3000),
        'total_roi': random.uniform(50, 200),
        'bets_placed': random.randint(80, 150),
        'winning_bets': random.randint(40, 80),
        'losing_bets': random.randint(30, 70),
        'win_rate': random.uniform(45, 60),
        'avg_stake': random.uniform(15, 35),
        'largest_win': random.uniform(30, 80),
        'largest_loss': random.uniform(-40, -15),
        'opportunities_found': random.randint(150, 250),
        'bet_conversion': random.uniform(50, 75),
        'avg_edge': random.uniform(0.06, 0.12),
        'min_edge': 0.05,
        'max_edge': random.uniform(0.15, 0.25),
        'current_drawdown': random.uniform(0, 10),
        'max_drawdown': random.uniform(5, 15),
        'peak_balance': random.uniform(2500, 3500),
        'avg_exposure': random.uniform(40, 70),
        'trend_7d': random.uniform(5, 15),
        'trend_30d': random.uniform(10, 20),
        'winrate_7d': random.uniform(50, 60),
        'by_selection': {
            'Natural Win': {
                'count': random.randint(50, 80),
                'win_rate': random.uniform(45, 60),
                'pnl': random.uniform(20, 80),
            },
            'Pocket Pair': {
                'count': random.randint(40, 70),
                'win_rate': random.uniform(40, 55),
                'pnl': random.uniform(10, 60),
            },
        },
        'api_uptime': random.uniform(98, 100),
        'avg_response_time': random.randint(50, 200),
        'errors_today': random.randint(0, 3),
        'alerts': [],
    }
    
    return generate_daily_report(date, data)


def main():
    print("=" * 80)
    print("AUTOMATED REPORTING SYSTEM")
    print("=" * 80)
    
    print("\nThis system generates comprehensive performance reports:")
    print("  • Daily P&L summaries")
    print("  • Win/loss statistics")
    print("  • Edge and risk analysis")
    print("  • Performance trends")
    print("  • Weekly summaries")
    
    print("\n" + "=" * 80)
    
    response = input("\nGenerate sample report? (y/n): ")
    if response.lower() == 'y':
        print("\nGenerating sample daily report...\n")
        report = generate_sample_report()
        print(report)
        
        filename = f"daily_report_{datetime.now().strftime('%Y%m%d')}.txt"
        filepath = save_report(report, filename)
        print(f"\n✓ Report saved to: {filepath}")
        
        print("\nTo integrate with your bot:")
        print("  1. Collect performance data during operation")
        print("  2. Call generate_daily_report() at end of day")
        print("  3. Save or email report automatically")
        print("  4. Set up cron/scheduled task for automation")
    else:
        print("\nTo use in production:")
        print("  • Import reporting functions into your bot")
        print("  • Collect metrics throughout the day")
        print("  • Schedule report generation (e.g., midnight)")
        print("  • Configure email delivery (optional)")


if __name__ == '__main__':
    main()
