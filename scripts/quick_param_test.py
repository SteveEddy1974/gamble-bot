#!/usr/bin/env python3
"""
Quick strategy tests with different parameters.
"""
import subprocess
import yaml
import time

def run_simulation(min_edge, max_exposure, iterations=2000):
    """Run bot with specific parameters."""
    # Read current config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Backup original values
    original_edge = config['bot']['min_edge']
    original_exposure = config['bot']['max_exposure_pct']
    
    # Set test parameters
    config['bot']['min_edge'] = min_edge
    config['bot']['max_exposure_pct'] = max_exposure
    
    # Write config
    with open('config.yaml', 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    # Run bot
    result = subprocess.run(
        ['python', 'main.py', str(iterations)],
        capture_output=True,
        text=True
    )
    
    # Restore original config
    config['bot']['min_edge'] = original_edge
    config['bot']['max_exposure_pct'] = original_exposure
    
    with open('config.yaml', 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    # Parse output
    output = result.stdout
    
    # Extract final balance
    for line in output.split('\n'):
        if 'Final balance:' in line:
            try:
                balance_str = line.split('£')[1].split()[0]
                final_balance = float(balance_str)
                return final_balance
            except:
                pass
    
    return None


def quick_parameter_test():
    """Test a few key parameter combinations."""
    print("=" * 80)
    print("QUICK PARAMETER TEST")
    print("=" * 80)
    print()
    
    tests = [
        {'min_edge': 0.03, 'max_exposure': 0.10, 'name': 'Lower edge threshold'},
        {'min_edge': 0.05, 'max_exposure': 0.10, 'name': 'Current settings'},
        {'min_edge': 0.07, 'max_exposure': 0.10, 'name': 'Higher edge threshold'},
        {'min_edge': 0.05, 'max_exposure': 0.05, 'name': 'Lower exposure'},
        {'min_edge': 0.05, 'max_exposure': 0.15, 'name': 'Higher exposure'},
    ]
    
    iterations = 2000
    start_balance = 1000
    
    print(f"Each test: {iterations} iterations, £{start_balance} starting balance")
    print()
    
    results = []
    
    for i, test in enumerate(tests, 1):
        print(f"Test {i}/{len(tests)}: {test['name']}")
        print(f"  Parameters: min_edge={test['min_edge']:.2%}, max_exposure={test['max_exposure']:.2%}")
        print(f"  Running...", end=' ', flush=True)
        
        start_time = time.time()
        final_balance = run_simulation(test['min_edge'], test['max_exposure'], iterations)
        elapsed = time.time() - start_time
        
        if final_balance:
            profit = final_balance - start_balance
            roi = (profit / start_balance) * 100
            
            results.append({
                'name': test['name'],
                'min_edge': test['min_edge'],
                'max_exposure': test['max_exposure'],
                'final_balance': final_balance,
                'roi': roi,
                'elapsed': elapsed
            })
            
            print(f"Done ({elapsed:.1f}s)")
            print(f"  Result: £{final_balance:.2f} ({roi:+.1f}% ROI)")
        else:
            print("Failed to parse result")
        
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print(f"{'Configuration':<30} {'Min Edge':<12} {'Max Exp':<12} {'ROI':<12} {'Final':<12}")
    print("-" * 80)
    
    for r in sorted(results, key=lambda x: x['roi'], reverse=True):
        print(f"{r['name']:<30} {r['min_edge']:.2%:<12} {r['max_exposure']:.2%:<12} "
              f"{r['roi']:+.1f}%{'':<7} £{r['final_balance']:.2f}")
    
    print()
    
    best = max(results, key=lambda x: x['roi'])
    print(f"Best performer: {best['name']}")
    print(f"  ROI: {best['roi']:+.1f}%")
    print(f"  Parameters: min_edge={best['min_edge']:.2%}, max_exposure={best['max_exposure']:.2%}")
    print()


if __name__ == '__main__':
    quick_parameter_test()
