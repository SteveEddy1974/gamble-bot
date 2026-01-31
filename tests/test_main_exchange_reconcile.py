import unittest
import tempfile
import os
import yaml
from lxml import etree
import main


class DummySim:
    def __init__(self, *a, **k):
        self._snap = b''
        # Simple card counts
        self.card_counts = {r: 32 for r in range(1, 14)}

    def get_snapshot(self, channel_id):
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
        # Return a cleared order that corresponds to betId '1'
        return {'result': {'clearedOrders': [{'betId': '1', 'betOutcome': 'WON', 'profit': 40.0, 'commissionPaid': 0.5, 'settledDate': '2026-01-01T00:00:00Z'}]}}


class TestMainExchangeReconcile(unittest.TestCase):
    def test_main_calls_reconcile_and_updates_state_csv(self):
        tmp_cfg = tempfile.NamedTemporaryFile(delete=False, suffix='.yaml')
        tmp_csv = tempfile.NamedTemporaryFile(delete=False, suffix='.csv')
        tmp_state = tempfile.NamedTemporaryFile(delete=False)
        tmp_cfg.close(); tmp_csv.close(); tmp_state.close()
        cfg = {
            'credentials': {'username': '', 'password': ''},
            'bot': {
                'min_edge': 0.0,
                'max_exposure_pct': 0.1,
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
        # Monkeypatch SimulatedAPIClient to our DummySim
        old_sim = main.SimulatedAPIClient
        main.SimulatedAPIClient = DummySim
        try:
            main.main(iterations=1, override_poll_interval=0.01)
            # State file should be saved and should include processed bet id from reconcile
            self.assertTrue(os.path.exists(tmp_state.name))
            with open(tmp_state.name, 'r', encoding='utf-8') as sf:
                txt = sf.read().strip()
                if txt:
                    self.assertIn('processed_bet_ids', txt)
            # CSV should exist and include betId
            with open(tmp_csv.name, 'r', encoding='utf-8') as cf:
                csv_txt = cf.read()
                self.assertIn('1', csv_txt)
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
