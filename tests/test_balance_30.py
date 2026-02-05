"""
Behavioral tests for low-balance scenarios (start balance £30).
These tests verify deterministic logic (stake sizing caps, BetManager checks,
and _eval_strategy returns well-formed stats) without evaluating or
optimizing for profit.
"""
from lxml import etree
import pytest

from engine import size_stake
from main import BetManager, is_balance_sufficient_for_live, parse_market_selections, parse_shoe_state
from scripts.dry_run_real_api import _selection_records, _eval_strategy


def load_fixture(path):
    with open(path, 'rb') as f:
        return etree.fromstring(f.read())


def test_size_stake_caps_with_low_balance():
    balance = 30.0
    max_exposure_pct = 0.1
    # Kelly example
    stake = size_stake(balance, max_exposure_pct, edge=0.2, price=5.0, true_prob=0.25, strategy='kelly', shrink=0.5)
    # caps
    assert stake <= balance
    assert stake <= balance * max_exposure_pct
    assert stake <= balance * 0.10  # default max_stake_pct used in engine

    # Proportional example
    stake_p = size_stake(balance, max_exposure_pct, edge=0.05, strategy='proportional')
    assert stake_p <= balance * max_exposure_pct
    assert stake_p >= 0


def test_bet_manager_and_safety_guard_under_30():
    balance = 30.0
    bm = BetManager(balance=balance, max_exposure=balance * 0.1)
    cfg = {'bot': {'min_stake': 1.0}}

    assert is_balance_sufficient_for_live(bm, cfg) is True

    # stake greater than balance should not be allowed
    assert bm.can_place(balance + 1.0) is False

    # small stake should be allowed
    assert bm.can_place(1.0) is True


def test_eval_strategy_handles_balance_30_fixture():
    # Use the deep fixture (has multiple selections) for deterministic behavior
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
        # fallback to marketSelections/marketSelections simple fixture
        selections_elem = root.find('.//bf:marketSelections', ns) or root.find('.//marketSelections')

    assert selections_elem is not None
    selections = parse_market_selections(selections_elem)
    shoe = parse_shoe_state(shoe_elem)

    records = _selection_records(selections, shoe)
    stats = _eval_strategy(records, start_balance=30.0, max_exposure_pct=0.1, min_edge=0.05, min_price=None, kelly_factor=0.05, trade_natural=True, trade_pocket=True)

    assert isinstance(stats, dict)
    for k in ('opportunities_found', 'would_place', 'would_skip_exposure', 'would_skip_balance'):
        assert k in stats
        assert isinstance(stats[k], int) and stats[k] >= 0
    assert 'total_would_stake' in stats
    assert isinstance(stats['total_would_stake'], float) and stats['total_would_stake'] >= 0.0
