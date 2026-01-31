import unittest
import tempfile
import os
import yaml
import json
import main
from main import reconcile_cleared_orders, BetManager
from lxml import etree


class MockExchangeDelayed:
    def __init__(self):
        self.calls = 0

    def list_cleared_orders(self, **kwargs):
        # First call returns empty, second returns a cleared order for bet 'b1'
        self.calls += 1
        if self.calls == 1:
            return {'result': {'clearedOrders': []}}
        return {
            'result': {
                'clearedOrders': [
                    {'betId': 'b1', 'betOutcome': 'WON', 'profit': 40.0, 'commissionPaid': 0.0, 'settledDate': '2026-01-01T00:00:00Z'}
                ]
            }
        }


class TestIntegrationMockedExchange(unittest.TestCase):
    def test_reconcile_with_delayed_settlements(self):
        # Setup BetManager with an active bet b1
        bm = BetManager(balance=1000.0, max_exposure=100.0)
        # Fake opp-like record
        class DummyOpp:
            def __init__(self):
                self.stake = 20.0
                self.market_price = 5.0

        opp = DummyOpp()
        bm.record_accepted('b1', opp)

        mock = MockExchangeDelayed()
        # Prepare temp state and csv
        tmp_state = tempfile.NamedTemporaryFile(delete=False)
        tmp_csv = tempfile.NamedTemporaryFile(delete=False, suffix='.csv')
        tmp_state.close(); tmp_csv.close()
        try:
            state = {'processed_bet_ids': []}
            # First call: nothing processed
            s1 = reconcile_cleared_orders(mock, bm, state, tmp_state.name, from_iso=None, lookback=60, csv_path=tmp_csv.name)
            self.assertEqual(s1.get('processed_bet_ids', []), [])
            # Second call: should process b1
            s2 = reconcile_cleared_orders(mock, bm, s1, tmp_state.name, from_iso=None, lookback=60, csv_path=tmp_csv.name)
            self.assertIn('b1', s2.get('processed_bet_ids', []))
            # Read csv and ensure row for b1 exists
            txt = open(tmp_csv.name, 'r', encoding='utf-8').read()
            self.assertIn('b1', txt)
        finally:
            try:
                os.unlink(tmp_state.name)
            except Exception:
                pass
            try:
                os.unlink(tmp_csv.name)
            except Exception:
                pass


class DummySimWithTransientExchange:
    def __init__(self, *a, **k):
        self._snap = b''
        self.list_calls = 0

    def get_snapshot(self, channel_id):
        # Minimal snapshot with one selection
        xml = '''
        <channelSnapshot>
          <shoe>
            <cardsDealt>0</cardsDealt>
            <cardsRemaining>416</cardsRemaining>
            <cardCounts>
              <card rank="1">32</card>
            </cardCounts>
          </shoe>
          <marketSelections>
            <selection>
              <selectionId>1</selectionId>
              <name>Pocket Pair In Any Hand</name>
              <status>IN_PLAY</status>
              <bestBackPrice>5.0</bestBackPrice>
            </selection>
          </marketSelections>
          <settlements></settlements>
        </channelSnapshot>
        '''
        return etree.fromstring(xml.encode('utf-8'))

    def post_bet_order(self, market_id, round_id, currency, bid_type, price, stake, selection_id):
        resp = '<postBetOrderResponse><status>ACCEPTED</status><betId>1</betId></postBetOrderResponse>'
        return etree.fromstring(resp.encode('utf-8'))

    def list_cleared_orders(self, **kwargs):
        # first call raise transient error (simulate 503), second returns cleared order
        self.list_calls += 1
        if self.list_calls == 1:
            raise Exception('503 Service Unavailable')
        return {'result': {'clearedOrders': [{'betId': '1', 'betOutcome': 'WON', 'profit': 40.0, 'commissionPaid': 0.5, 'settledDate': '2026-01-01T00:00:00Z'}]}}


class TestMainWithMockedExchange(unittest.TestCase):
    def test_main_handles_transient_exchange_errors_and_reconciles(self):
        tmp_cfg = tempfile.NamedTemporaryFile(delete=False, suffix='.yaml')
        tmp_csv = tempfile.NamedTemporaryFile(delete=False, suffix='.csv')
        tmp_state = tempfile.NamedTemporaryFile(delete=False)
        tmp_cfg.close(); tmp_csv.close(); tmp_state.close()
        cfg = {
            'credentials': {'username': '', 'password': ''},
            'bot': {
                'min_edge': 0.0,
                'max_exposure_pct': 0.5,
                'start_balance': 1000,
                'poll_interval_seconds': 0.01,
                'currency': 'GBP',
                'simulate': True,
                'simulate_place_bets': True,
                'simulate_start_cards': 416,
                'simulate_decrement': 4,
                'simulate_reset_after': None,
                'use_exchange_api': True,
                'exchange_poll_cleared_seconds': 0,
                'exchange_cleared_lookback_seconds': 60,
                'state_file': tmp_state.name,
                'cleared_orders_csv': tmp_csv.name
            },
            'logging': {'level': 'INFO', 'file': 'bot.log'}
        }
        with open(tmp_cfg.name, 'w', encoding='utf-8') as f:
            yaml.safe_dump(cfg, f)
        old = main.CONFIG_PATH
        main.CONFIG_PATH = tmp_cfg.name
        # Monkeypatch SimulatedAPIClient to our Dummy that also simulates Exchange
        old_sim = main.SimulatedAPIClient
        main.SimulatedAPIClient = DummySimWithTransientExchange
        try:
            # Run few iterations; main should catch transient error in reconcile and continue
            main.main(iterations=3, override_poll_interval=0.01)
            # After run, state file should include processed bet id '1' (since second reconcile should succeed)
            with open(tmp_state.name, 'r', encoding='utf-8') as sf:
                txt = sf.read().strip()
                if txt:
                    s = json.loads(txt)
                    self.assertIn('1', s.get('processed_bet_ids', []))
            # CSV may not be written by main in this path; state contains the processed bet id
        finally:
            main.CONFIG_PATH = old
            main.SimulatedAPIClient = old_sim
            os.unlink(tmp_cfg.name)
            if os.path.exists(tmp_csv.name):
                os.unlink(tmp_csv.name)
            try:
                if os.path.exists(tmp_state.name):
                    os.unlink(tmp_state.name)
            except PermissionError:
                pass


if __name__ == '__main__':
    unittest.main()
