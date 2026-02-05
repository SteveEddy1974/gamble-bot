#!/usr/bin/env python3
"""Dry-run simulation harness to evaluate profitability over N iterations.

Usage: python scripts/dry_run.py [iterations]
"""
import sys
import os
# ensure project root is on path when executed from scripts/
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from main import parse_shoe_state, parse_market_selections, prob_pocket_pair, prob_natural_win, evaluate, size_stake, BetManager, Executor, SimulatedAPIClient


def run_dry(iterations=1000, start_balance=1000, max_exposure_pct=0.1, channel_id='dummy_channel'):
    # Enable continuous shoe resets every 50 iterations with faster settlements
    # This simulates multiple fresh shoes throughout the test
    sim = SimulatedAPIClient(start_cards_remaining=416, reset_after=50, settle_delay=1, decrement=4)
    executor = Executor(sim, currency='GBP')
    bet_manager = BetManager(start_balance, start_balance * max_exposure_pct)

    stats = {'placed': 0, 'accepted': 0, 'settled_won': 0, 'settled_lost': 0}

    for i in range(iterations):
        # Progress indicator every 10 iterations
        if (i + 1) % 10 == 0:
            print(f"Progress: {i+1}/{iterations} iterations, Placed: {stats['placed']}, Balance: {bet_manager.balance:.2f}", flush=True)
        xml_root = sim.get_snapshot(channel_id)
        shoe = parse_shoe_state(xml_root.find('shoe'))
        selections = parse_market_selections(xml_root.find('marketSelections'))

        # Process settlements
        settlements_elem = xml_root.find('settlements')
        if settlements_elem is not None:
            for s in settlements_elem.findall('settlement'):
                bet_id = s.find('betId').text if s.find('betId') is not None else None
                status = s.find('status').text if s.find('status') is not None else None
                payout = float(s.find('payout').text) if s.find('payout') is not None else 0.0
                profit = None
                if bet_id is not None:
                    res = bet_manager.process_settlement(bet_id, status, payout)
                    if res is not None:
                        if res > 0:
                            stats['settled_won'] += 1
                        else:
                            stats['settled_lost'] += 1

        # Evaluate simple opportunities
        for sel in selections:
            if sel.status != 'IN_PLAY':
                continue
            if sel.name == 'Pocket Pair In Any Hand' and sel.best_back_price:
                prob = prob_pocket_pair(shoe)
                ok, edge = evaluate(sel, prob, sel.best_back_price, 'BACK')
            elif sel.name == 'Natural Win' and sel.best_back_price:
                prob = prob_natural_win(shoe)
                ok, edge = evaluate(sel, prob, sel.best_back_price, 'BACK')
            else:
                continue
            if not ok:
                continue
            stake = size_stake(bet_manager.balance, max_exposure_pct, edge, price=sel.best_back_price, true_prob=prob)
            if stake <= 0:
                continue
            if not bet_manager.can_place(stake):
                continue
            # Place simulated bet
            resp = executor.place_bet('m', 'r', type('O', (), {'selection': sel, 'action': 'BACK', 'market_price': sel.best_back_price, 'stake': stake}) )
            stats['placed'] += 1
            # detect accepted
            status_el = resp.find('status') if resp is not None else None
            status = status_el.text if status_el is not None else str(resp)
            if status == 'ACCEPTED':
                bet_id_el = resp.find('betId')
                bet_id = bet_id_el.text if bet_id_el is not None else None
                if bet_id:
                    bet_manager.record_accepted(bet_id, type('O', (), {'stake': stake, 'market_price': sel.best_back_price, 'selection': sel}))
                    stats['accepted'] += 1

    # Final settlement sweep
    for _ in range(10):
        xml_root = sim.get_snapshot(channel_id)
        settlements_elem = xml_root.find('settlements')
        if settlements_elem is not None:
            for s in settlements_elem.findall('settlement'):
                bet_id = s.find('betId').text if s.find('betId') is not None else None
                status = s.find('status').text if s.find('status') is not None else None
                payout = float(s.find('payout').text) if s.find('payout') is not None else 0.0
                if bet_id is not None:
                    res = bet_manager.process_settlement(bet_id, status, payout)
                    if res is not None:
                        if res > 0:
                            stats['settled_won'] += 1
                        else:
                            stats['settled_lost'] += 1
    return bet_manager, stats


if __name__ == '__main__':
    iters = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    bm, s = run_dry(iters)
    print('Iterations:', iters)
    print('Placed:', s['placed'], 'Accepted:', s['accepted'])
    print('Settled wins:', s['settled_won'], 'losses:', s['settled_lost'])
    print('Final balance:', bm.balance)
    print('PnL:', bm.pnl)
