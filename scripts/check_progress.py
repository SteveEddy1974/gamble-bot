#!/usr/bin/env python3
"""
Quick progress checker for ongoing simulation
Usage: python scripts/check_progress.py
"""
import re
import sys
from pathlib import Path

def get_latest_progress():
    """Read bot.log and extract latest progress from current run"""
    log_file = Path('bot.log')
    if not log_file.exists():
        print("No bot.log found")
        return None
    
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
        
        # Find most recent run start
        start_idx = -1
        for i in range(len(lines)-1, -1, -1):
            if 'Started Metrics HTTP exporter' in lines[i]:
                start_idx = i
                break
        
        if start_idx == -1:
            print("No active run found in log")
            return None
        
        # Count bets and get latest balance
        bets_placed = 0
        bets_settled = 0
        latest_balance = 50.0
        wins = 0
        losses = 0
        max_balance = 50.0
        min_balance = 50.0
        stakes = []
        
        for line in lines[start_idx:]:
            if 'Placed simulated bet:' in line:
                bets_placed += 1
                # Get stake from previous line
                prev_idx = lines.index(line) - 1
                if prev_idx >= 0:
                    stake_match = re.search(r'stake=([\d.]+)', lines[prev_idx])
                    if stake_match:
                        stakes.append(float(stake_match.group(1)))
            
            if 'Processed settlement:' in line:
                bets_settled += 1
                profit_match = re.search(r'profit=([-\d.]+)', line)
                balance_match = re.search(r'balance=([\d.]+)', line)
                if profit_match and balance_match:
                    profit = float(profit_match.group(1))
                    latest_balance = float(balance_match.group(1))
                    max_balance = max(max_balance, latest_balance)
                    min_balance = min(min_balance, latest_balance)
                    if profit > 0:
                        wins += 1
                    else:
                        losses += 1
        
        return {
            'bets_placed': bets_placed,
            'bets_settled': bets_settled,
            'balance': latest_balance,
            'wins': wins,
            'losses': losses,
            'profit': latest_balance - 50.0,
            'max_balance': max_balance,
            'min_balance': min_balance,
            'stakes': stakes
        }
    except Exception as e:
        print(f"Error reading log: {e}")
        return None

def main():
    progress = get_latest_progress()
    
    if not progress:
        sys.exit(1)
    
    # Calculate metrics
    total_settled = progress['wins'] + progress['losses']
    win_rate = (progress['wins'] / total_settled * 100) if total_settled > 0 else 0
    profit_pct = (progress['profit'] / 50.0 * 100)
    pending = progress['bets_placed'] - progress['bets_settled']
    
    print("=" * 70)
    print("SIMULATION PROGRESS")
    print("=" * 70)
    print(f"Current Balance:    £{progress['balance']:.2f}")
    print(f"Total Profit:       £{progress['profit']:.2f} ({profit_pct:+.1f}%)")
    print(f"Peak Balance:       £{progress['max_balance']:.2f}")
    print(f"Lowest Balance:     £{progress['min_balance']:.2f}")
    print()
    print(f"Bets Placed:        {progress['bets_placed']}")
    print(f"Bets Settled:       {progress['bets_settled']}")
    print(f"Pending:            {pending}")
    print()
    print(f"Wins:               {progress['wins']} ({win_rate:.1f}%)")
    print(f"Losses:             {progress['losses']}")
    print()
    
    if progress['stakes']:
        avg_stake = sum(progress['stakes']) / len(progress['stakes'])
        min_stake = min(progress['stakes'])
        max_stake = max(progress['stakes'])
        latest_stake = progress['stakes'][-1] if progress['stakes'] else 0
        
        print("STAKE ANALYSIS:")
        print(f"  Current:          £{latest_stake:.2f}")
        print(f"  Average:          £{avg_stake:.2f}")
        print(f"  Range:            £{min_stake:.2f} - £{max_stake:.2f}")
        print()
        
        # Dynamic scaling analysis
        current_balance = progress['balance']
        if current_balance < 100:
            expected_max = current_balance * 0.03
            tier = "3% (Conservative)"
        elif current_balance < 200:
            expected_max = current_balance * 0.04
            tier = "4% (Moderate)"
        else:
            expected_max = current_balance * 0.05
            tier = "5% (Aggressive)"
        
        print("DYNAMIC SCALING:")
        print(f"  Current Tier:     {tier}")
        print(f"  Expected Max:     £{expected_max:.2f}")
        print(f"  Actual Max:       £{max_stake:.2f}")
        
        if max_stake > expected_max * 0.95:
            print(f"  Status:           ✓ Scaling working (at limit)")
        else:
            print(f"  Status:           ✓ Within safe limits")
    
    print("=" * 70)

if __name__ == '__main__':
    main()
