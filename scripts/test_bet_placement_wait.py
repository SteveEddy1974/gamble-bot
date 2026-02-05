#!/usr/bin/env python3
"""Wait for an ACTIVE market and place a single above-minimum test bet, logging full HTTP details."""
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import load_config
from api_client import APIClient
from lxml import etree

config = load_config()
api_client = APIClient(config['credentials'])

CHANNEL = '1444086'
TIMEOUT = 120  # seconds
POLL = 2

def get_full_snapshot(client: APIClient, channel_id: str):
    username = config['credentials'].get('username')
    url = f"https://api.games.betfair.com/rest/v1/channels/{channel_id}/snapshot?username={username}"
    resp = client.session.get(url)
    resp.raise_for_status()
    return etree.fromstring(resp.content)


start = time.time()
print(f"Waiting up to {TIMEOUT}s for SideBets market to become ACTIVE with prices...")
while time.time() - start < TIMEOUT:
    snapshot = get_full_snapshot(api_client, CHANNEL)
    ns = {'bf': 'urn:betfair:games:api:v1'}

    markets_elem = snapshot.find('.//bf:markets', ns)
    if markets_elem is None:
        markets_elem = snapshot.find('.//markets')
    if markets_elem is None:
        print('No markets element found; retrying...')
        time.sleep(POLL)
        continue

    side_market = None
    for m in markets_elem.findall('.//bf:market', ns) or markets_elem.findall('.//market'):
        selections_elem = m.find('.//bf:selections', ns)
        if selections_elem is None:
            selections_elem = m.find('.//selections')
        if selections_elem is None:
            continue
        sel_type = selections_elem.get('type')
        if sel_type == 'SideBets':
            side_market = m
            break

    if side_market is None:
        print('No SideBets market found; retrying...')
        time.sleep(POLL)
        continue

    status_elem = side_market.find('.//bf:status', ns)
    if status_elem is None:
        status_elem = side_market.find('.//status')
    market_status = status_elem.text if status_elem is not None else 'UNKNOWN'
    print(f"SideBets market status: {market_status}")
    if market_status != 'ACTIVE':
        time.sleep(POLL)
        continue

    selections = side_market.find('.//bf:selections', ns)
    if selections is None:
        selections = side_market.find('.//selections')

    chosen = None
    if selections is not None:
        for sel in selections.findall('.//bf:selection', ns) or selections.findall('.//selection'):
            back_prices = sel.find('.//bf:bestAvailableToBackPrices', ns)
            if back_prices is None:
                back_prices = sel.find('.//bestAvailableToBackPrices')
            if back_prices is None:
                continue
            first_price = back_prices.find('.//bf:price', ns)
            if first_price is None:
                first_price = back_prices.find('.//price')
            if first_price is not None and first_price.text:
                chosen = (sel, float(first_price.text))
                break

    if not chosen:
        print('No selection with a back price found; retrying...')
        time.sleep(POLL)
        continue

    sel, price = chosen
    sel_id = sel.get('id')
    name_elem = sel.find('.//bf:name', ns) or sel.find('.//name')
    name = name_elem.text if name_elem is not None else 'Unknown'
    market_id = side_market.get('id')
    game_elem = snapshot.find('.//bf:game', ns)
    if game_elem is None:
        game_elem = snapshot.find('.//game')
    round_elem = None
    if game_elem is not None:
        round_elem = game_elem.find('.//bf:round', ns)
        if round_elem is None:
            round_elem = game_elem.find('.//round')
    round_id = round_elem.text if round_elem is not None else '1'

    print(f"Placing test bet: market={market_id}, round={round_id}, sel={sel_id} ({name}), price={price}")
    stake = 2.0
    try:
        res = api_client.post_bet_order(
            market_id=market_id,
            round_id=round_id,
            currency='GBP',
            bid_type='BACK',
            price=price,
            stake=stake,
            selection_id=sel_id,
        )
        import xml.etree.ElementTree as ET
        print('SUCCESS:', ET.tostring(res, encoding='unicode'))
    except Exception as e:
        print('Placement failed:', e)
    break
else:
    print('Timed out waiting for ACTIVE market.')
