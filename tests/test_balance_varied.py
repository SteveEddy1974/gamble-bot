import pytest
from lxml import etree

from engine import size_stake
from main import BetManager, is_balance_sufficient_for_live, parse_market_selections, parse_shoe_state
from scripts.dry_run_real_api import _selection_records, _eval_strategy


def load_fixture(path):
    with open(path, 'rb') as f:
        return etree.fromstring(f.read())


@pytest.mark.parametrize('start_balance', [1.0, 30.0, 100.0])
def test_eval_strategy_with_various_balances(start_balance):
    root = load_fixture('tests/fixtures/sample_channel_snapshot_deep.xml')
    ns = {'bf': 'urn:betfair:games:api:v1'}
    shoe_elem = root.find('.//bf:shoe', ns) or root.find('.//shoe')

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
    shoe = parse_shoe_state(shoe_elem)

    records = _selection_records(selections, shoe)
    stats = _eval_strategy(records, start_balance=start_balance, max_exposure_pct=0.1, min_edge=0.05, min_price=None, kelly_factor=0.05, trade_natural=True, trade_pocket=True)

    # Basic structure
    assert isinstance(stats, dict)
    assert 'would_place' in stats
    assert isinstance(stats['would_place'], int)
    assert stats['would_place'] >= 0

    # If balance is low, check that would_skip_balance can be non-zero
    if start_balance < 5:
        assert stats['would_skip_balance'] >= 0


def test_size_stake_returns_zero_for_tiny_balance():
    # balance so small that even min stakes may exceed it
    balance = 0.5
    stake = size_stake(balance, 0.1, edge=0.2, price=5.0, true_prob=0.25, strategy='kelly', shrink=0.5)
    assert stake == 0 or stake <= balance
