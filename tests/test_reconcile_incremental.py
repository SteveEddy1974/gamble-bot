import unittest
from unittest.mock import MagicMock
from main import reconcile_cleared_orders
from main import BetManager


class TestReconcileIncremental(unittest.TestCase):
    def test_reconcile_uses_settledDateRange_and_updates_timestamp(self):
        mock_api = MagicMock()
        # Create two cleared orders with settledDate fields
        c1 = {'betId': '1', 'profit': 10.0, 'commissionPaid': 0.0, 'settledDate': '2026-01-30T12:00:00Z'}
        c2 = {'betId': '2', 'profit': 5.0, 'commissionPaid': 0.0, 'settledDate': '2026-01-30T12:05:00Z'}
        mock_api.list_cleared_orders.return_value = {'result': {'clearedOrders': [c1, c2]}}

        bm = BetManager(balance=1000, max_exposure=100)
        # Pre-record bets so process_cleared_order can find them
        opp = MagicMock()
        opp.stake = 20.0
        opp.market_price = 2.0
        bm.record_accepted('1', opp)

        opp2 = MagicMock()
        opp2.stake = 10.0
        opp2.market_price = 2.5
        bm.record_accepted('2', opp2)

        import tempfile
        import os
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.close()
        state_file = tmp.name
        try:
            state = {'last_cleared_timestamp': None, 'processed_bet_ids': []}
            state = reconcile_cleared_orders(mock_api, bm, state, state_file, from_iso=None, lookback=3600)
            self.assertIsNotNone(state.get('last_cleared_timestamp'))
            self.assertTrue(state.get('last_cleared_timestamp').startswith('2026-01-30T12:05'))
            self.assertIn('1', state.get('processed_bet_ids'))
            self.assertIn('2', state.get('processed_bet_ids'))
            # check balances updated (stake reserved removed + profit applied):
            # start 1000 -> -20 -10 = 970, then +20+10 -> 1000, then +10+5 -> 1015
            self.assertAlmostEqual(bm.balance, 1015.0)
        finally:
            os.unlink(state_file)


if __name__ == '__main__':
    unittest.main()
