import unittest
from unittest.mock import MagicMock
from main import BetManager


class TestReconcile(unittest.TestCase):
    def test_reconcile_cleared_orders(self):
        # Setup BetManager with an active bet
        bm = BetManager(balance=1000, max_exposure=100)
        # create a fake opp-like record and record it
        opp = MagicMock()
        opp.stake = 20.0
        opp.market_price = 5.0
        bm.record_accepted('100', opp)
        # Mock exchange client returning clearedOrders with net profit
        mock_client = MagicMock()
        cleared = [{'betId': '100', 'betOutcome': 'WON', 'profit': 80.0, 'commissionPaid': 0.0}]
        mock_client.list_cleared_orders.return_value = {'result': {'clearedOrders': cleared}}
        # Call reconcile logic (mimic main behaviour)
        res = mock_client.list_cleared_orders(betStatus='SETTLED')
        cleared_list = res.get('result', {}).get('clearedOrders', [])
        for c in cleared_list:
            profit = bm.process_cleared_order(c)
            self.assertEqual(profit, 80.0)
            self.assertEqual(bm.balance, 1080.0)  # initial 1000 - stake 20 + stake + profit
            self.assertEqual(bm.current_exposure, 0.0)


if __name__ == '__main__':
    unittest.main()
