#!/usr/bin/env python3
"""Diagnose why opportunities aren't appearing - show raw prices and calculated edges."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import load_config, parse_shoe_state, parse_market_selections, prob_pocket_pair, prob_natural_win
from api_client import APIClient
from engine import evaluate


def diagnose(channel_id, samples=10):
    """Show detailed breakdown of prices vs probabilities."""
    config = load_config()
    api_client = APIClient(config['credentials'])
    min_edge = config['bot'].get('min_edge', 0.05)
    
    print(f"=== OPPORTUNITY DIAGNOSTICS ===")
    print(f"Channel: {channel_id}")
    print(f"Min Edge Required: {min_edge*100}%")
    print(f"Samples: {samples}")
    print("=" * 80)
    print()
    
    import time
    ns = {'bf': 'urn:betfair:games:api:v1'}
    
    for i in range(samples):
        try:
            xml_root = api_client.get_snapshot(channel_id)
            
            # Get shoe
            game_data = xml_root.find('.//bf:gameData', ns)
            if game_data is None:
                game_data = xml_root.find('.//gameData')
            
            shoe_elem = None
            if game_data is not None:
                for obj in game_data.findall('.//bf:object', ns):
                    if obj.get('name') == 'Shoe':
                        shoe_elem = obj
                        break
                if shoe_elem is None:
                    for obj in game_data.findall('.//object'):
                        if obj.get('name') == 'Shoe':
                            shoe_elem = obj
                            break
            
            if shoe_elem is None:
                print(f"[{i+1}] No shoe data")
                time.sleep(3)
                continue
            
            shoe = parse_shoe_state(shoe_elem)
            
            # Get selections
            markets = xml_root.find('.//bf:markets', ns) or xml_root.find('.//markets')
            market = None
            if markets is not None:
                market = markets.find('.//bf:market', ns) or markets.find('.//market')
            
            selections_elem = None
            if market is not None:
                selections_elem = market.find('.//bf:selections', ns) or market.find('.//selections')
            
            if selections_elem is None:
                print(f"[{i+1}] No selections")
                time.sleep(3)
                continue
            
            selections = parse_market_selections(selections_elem)
            
            print(f"\n[Sample {i+1}] Cards Remaining: {shoe.cards_remaining}")
            print("-" * 80)
            
            for sel in selections:
                if sel.name == 'Pocket Pair In Any Hand' and sel.best_back_price:
                    true_prob = prob_pocket_pair(shoe)
                    implied_prob = 1.0 / sel.best_back_price if sel.best_back_price > 0 else 0
                    edge = true_prob - implied_prob
                    ok, calc_edge = evaluate(sel, true_prob, sel.best_back_price, 'BACK')
                    
                    print(f"  📊 {sel.name}")
                    print(f"     Market Price: {sel.best_back_price:.2f}")
                    print(f"     Implied Prob: {implied_prob*100:.2f}%")
                    print(f"     True Prob: {true_prob*100:.2f}%")
                    print(f"     Edge: {edge*100:.2f}%")
                    print(f"     Status: {'✅ OPPORTUNITY' if ok else f'❌ Below threshold ({min_edge*100}%)'}")
                
                elif sel.name == 'Natural Hand Win Any Hand' and sel.best_back_price:
                    true_prob = prob_natural_win(shoe)
                    implied_prob = 1.0 / sel.best_back_price if sel.best_back_price > 0 else 0
                    edge = true_prob - implied_prob
                    ok, calc_edge = evaluate(sel, true_prob, sel.best_back_price, 'BACK')
                    
                    print(f"  📊 {sel.name}")
                    print(f"     Market Price: {sel.best_back_price:.2f}")
                    print(f"     Implied Prob: {implied_prob*100:.2f}%")
                    print(f"     True Prob: {true_prob*100:.2f}%")
                    print(f"     Edge: {edge*100:.2f}%")
                    print(f"     Status: {'✅ OPPORTUNITY' if ok else f'❌ Below threshold ({min_edge*100}%)'}")
            
            time.sleep(3)
            
        except Exception as e:
            print(f"[{i+1}] Error: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(3)
    
    print("\n" + "=" * 80)
    print("Diagnostics complete.")


if __name__ == '__main__':
    channel_id = sys.argv[1] if len(sys.argv) > 1 else '1444086'
    samples = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    diagnose(channel_id, samples)
