#!/usr/bin/env python3
"""Automated betting script - starts Chrome and places bet automatically."""
import subprocess
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from main import load_config

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--bet-type', default="Pocket Pair In Any Hand")
    parser.add_argument('--price', type=float, default=10)
    parser.add_argument('--stake', type=float, default=0.5)
    args = parser.parse_args()

    print("="*60)
    print("AUTOMATED BET PLACEMENT")
    print("="*60)
    print(f"Bet: {args.bet_type}")
    print(f"Price: {args.price}")
    print(f"Stake: £{args.stake}")
    print("="*60)

    # Kill any existing Chrome processes to start fresh
    print("\n1. Preparing Chrome...")
    subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], capture_output=True)
    time.sleep(1)

    print("\n2. Running Selenium placer...")
    venv_python = r"C:/WORK-HTML/GAMBLE-BOT-30-01-2026/.venv/Scripts/python.exe"
    placer_script = "scripts/selenium_placer.py"
    
    cmd = [
        venv_python,
        placer_script,
        "--bet-type", args.bet_type,
        "--price", str(args.price),
        "--stake", str(args.stake),
        "--auto-submit",
        "--skip-confirm"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode == 0:
            print("\n" + "="*60)
            print("BET PLACEMENT COMPLETED SUCCESSFULLY!")
            print("="*60)
            return 0
        else:
            print("\n" + "="*60)
            print(f"BET PLACEMENT FAILED (exit code {result.returncode})")
            print("="*60)
            return 1
    except subprocess.TimeoutExpired:
        print("ERROR: Placer script timed out")
        return 1
    except Exception as e:
        print(f"ERROR: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
