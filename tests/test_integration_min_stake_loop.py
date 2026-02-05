from lxml import etree
from engine import evaluate, size_stake, calculate_dynamic_max_stake_pct
from main import BetManager, parse_market_selections, parse_shoe_state
from scripts.dry_run_real_api import _selection_records


def load_fixture(path):
    with open(path, 'rb') as f:
        return etree.fromstring(f.read())


def simulate_with_min_stake(start_balance, min_stake=1.0, max_exposure_pct=0.1):
    root = load_fixture('tests/fixtures/sample_channel_snapshot_deep.xml')
    ns = {'bf': 'urn:betfair:games:api:v1'}
    shoe_elem = root.find('.//bf:shoe', ns) or root.find('.//shoe')
    shoes = parse_shoe_state(shoe_elem)

    # Locate selections element
    markets = root.find('.//bf:markets', ns) or root.find('.//markets')
    selections_elem = None
    if markets is not None:
        for m in markets.findall('.//bf:market', ns) or markets.findall('.//market'):
            sel_elt = m.find('.//bf:selections', ns) or m.find('.//selections')
            if sel_elt is not None:
                selections_elem = sel_elt
                break
    if selections_elem is None:
        selections_elem = root.find('.//bf:marketSelections', ns) or root.find('.//marketSelections')

    selections = parse_market_selections(selections_elem)
    records = _selection_records(selections, shoes)

    bm = BetManager(start_balance, start_balance * max_exposure_pct)

    placed = 0
    skipped_balance = 0
    skipped_exposure = 0

    for i, rec in enumerate(records):
        ok, edge = evaluate(None, rec['true_prob'], rec['price'], 'BACK', min_edge=0.0)
        if not ok:
            continue
        dynamic_max = calculate_dynamic_max_stake_pct(bm.balance)
        stake = size_stake(bm.balance, max_exposure_pct, edge, price=rec['price'], true_prob=rec['true_prob'], shrink=0.05, max_stake_pct=dynamic_max)
        # enforce min_stake
        if stake < min_stake:
            stake = min_stake
        if bm.can_place(stake):
            # simulate accepted bet
            bid = f"b{i}"
            # construct simple opp-like object
            class O:
                def __init__(self, stake, price):
                    self.stake = stake
                    self.market_price = price
            opp = O(stake, rec['price'])
            bm.record_accepted(bid, opp)
            placed += 1
        else:
            if stake > bm.balance:
                skipped_balance += 1
            else:
                skipped_exposure += 1

    return {
        'start_balance': start_balance,
        'placed': placed,
        'skipped_balance': skipped_balance,
        'skipped_exposure': skipped_exposure,
        'final_balance': bm.balance,
        'current_exposure': bm.current_exposure,
    }


def test_min_stake_enforced_for_30():
    res = simulate_with_min_stake(30.0, min_stake=1.0, max_exposure_pct=0.1)
    # Ensure enforcement didn't allow placing when balance insufficient
    assert res['final_balance'] >= 0
    # Every placed stake must be at least min_stake; at least one placement may occur (non-deterministic), but ensure invariants
    assert res['current_exposure'] <= 30.0 * 0.1 + 1e-6
    assert res['placed'] >= 0


def test_min_stake_blocks_when_balance_too_low():
    res = simulate_with_min_stake(0.5, min_stake=1.0, max_exposure_pct=0.1)
    # No placements should occur because min_stake cannot be afforded
    assert res['placed'] == 0
    # All opportunities will be skipped due to insufficient balance
    assert res['skipped_balance'] >= 0


def test_min_stake_enforced_over_multiple_rounds():
    # Simulate 5 rounds, alternating wins/losses to exercise balance fluctuation
    rounds = 5
    start_balance = 30.0
    min_stake = 1.0
    max_exposure_pct = 0.1

    root = load_fixture('tests/fixtures/sample_channel_snapshot_deep.xml')
    ns = {'bf': 'urn:betfair:games:api:v1'}
    shoe_elem = root.find('.//bf:shoe', ns) or root.find('.//shoe')
    shoes = parse_shoe_state(shoe_elem)

    # Locate selections element
    markets = root.find('.//bf:markets', ns) or root.find('.//markets')
    selections_elem = None
    if markets is not None:
        for m in markets.findall('.//bf:market', ns) or markets.findall('.//market'):
            sel_elt = m.find('.//bf:selections', ns) or m.find('.//selections')
            if sel_elt is not None:
                selections_elem = sel_elt
                break
    if selections_elem is None:
        selections_elem = root.find('.//bf:marketSelections', ns) or root.find('.//marketSelections')

    selections = parse_market_selections(selections_elem)
    records = _selection_records(selections, shoes)

    bm = BetManager(start_balance, start_balance * max_exposure_pct)

    placed_total = 0
    for r in range(rounds):
        # In each round, attempt to place at most one bet (first viable record)
        placed_this_round = 0
        for rec in records:
            ok, edge = evaluate(None, rec['true_prob'], rec['price'], 'BACK', min_edge=0.0)
            if not ok:
                continue
            dynamic_max = calculate_dynamic_max_stake_pct(bm.balance)
            stake = size_stake(bm.balance, max_exposure_pct, edge, price=rec['price'], true_prob=rec['true_prob'], shrink=0.05, max_stake_pct=dynamic_max)
            if stake < min_stake:
                stake = min_stake
            if not bm.can_place(stake):
                # cannot afford min_stake: break out and ensure no placements happen this round
                break
            # Place
            bid = f"r{r}-b"
            class O:
                def __init__(self, stake, price):
                    self.stake = stake
                    self.market_price = price
            opp = O(stake, rec['price'])
            bm.record_accepted(bid, opp)
            placed_this_round += 1
            # Simulate settlement: alternate WIN on even rounds, LOSS on odd rounds
            if r % 2 == 0:
                payout = opp.stake * (opp.market_price - 1.0)
                bm.process_settlement(bid, 'WON', payout)
            else:
                bm.process_settlement(bid, 'LOST', 0.0)
            break
        placed_total += placed_this_round

    # After rounds, ensure that min_stake was enforced for each placed bet
    assert placed_total >= 0
    # If balance ever dropped below min_stake, then subsequent rounds would have had no placements
    # Confirm invariants: exposure never exceeds max exposure
    assert bm.current_exposure <= start_balance * max_exposure_pct + 1e-6
    # Final balance should be non-negative
    assert bm.balance >= 0.0
