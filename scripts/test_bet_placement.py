#!/usr/bin/env python3
"""Test bet placement with real live market data."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import load_config
from api_client import APIClient

config = load_config()
api_client = APIClient(config['credentials'])

# First get live snapshot to extract real market/round/selection IDs
try:
    print("Fetching live snapshot...")
    snapshot = api_client.get_snapshot('1444086')
    
    # Define namespace
    ns = {'bf': 'urn:betfair:games:api:v1'}
    
    # Get game/round info
    game_elem = snapshot.find('.//bf:game', ns) or snapshot.find('.//game')
    if game_elem is not None:
        round_id = game_elem.find('.//bf:round', ns)
        if round_id is None:
            round_id = game_elem.find('.//round')
        round_id = round_id.text if round_id is not None else game_elem.get('round', '1')
        print(f"Round ID: {round_id}")
    
    # Get market info
    market = snapshot.find('.//bf:market', ns) or snapshot.find('.//market')
    if market is not None:
        market_id = market.get('id')
        status_elem = market.find('.//bf:status', ns) or market.find('.//status')
        market_status = status_elem.text if status_elem is not None else 'UNKNOWN'
        print(f"Market ID: {market_id}  (status: {market_status})")
        
        # Only attempt placement if market is ACTIVE
        if market_status != 'ACTIVE':
            print("Market not ACTIVE - skipping bet placement. Try again when status is ACTIVE.")
        else:
            # Get a selection with prices
            selections = market.find('.//bf:selections', ns) or market.find('.//selections')
            chosen = None
            if selections is not None:
                for sel in selections.findall('.//bf:selection', ns) or selections.findall('.//selection'):
                    sel_status = (sel.find('.//bf:status', ns) or sel.find('.//status'))
                    if sel_status is not None and sel_status.text == 'IN_PLAY':
                        back_prices = sel.find('.//bf:bestAvailableToBackPrices', ns) or sel.find('.//bestAvailableToBackPrices')
                        first_price = None
                        if back_prices is not None:
                            first_price = back_prices.find('.//bf:price', ns) or back_prices.find('.//price')
                        if first_price is not None and first_price.text:
                            chosen = (sel, float(first_price.text))
                            break
            if not chosen:
                print('No IN_PLAY selection with a back price found; aborting.')
            else:
                sel, price = chosen
                sel_id = sel.get('id')
                name_elem = sel.find('.//bf:name', ns) or sel.find('.//name')
                name = name_elem.text if name_elem is not None else 'Unknown'
                print(f"Selection: {name} (ID: {sel_id})")
                print(f"Price: {price}")
                print()
                stake = 2.00  # use minimum stake for testing
                print(f"Attempting to place £{stake:.2f} test bet...")
                try:
                    result = api_client.post_bet_order(
                        market_id=market_id,
                        round_id=round_id,
                        currency="GBP",
                        bid_type="B",
                        price=price,
                        stake=stake,
                        selection_id=sel_id
                    )
                    print("✅ SUCCESS! Bet placed!")
                    import xml.etree.ElementTree as ET
                    print(ET.tostring(result, encoding='unicode'))
                except Exception as e:
                    print(f"Placement failed: {e}")
                    # The api_client now prints debug info on failure
                    raise
                
except Exception as e:
    print(f"❌ Error: {e}")
    if hasattr(e, 'response') and e.response is not None:
        print(f"Status: {e.response.status_code}")
        print(f"Response: {e.response.text}")
