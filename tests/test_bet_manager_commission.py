import unittest
from main import BetManager
from models import Opportunity, MarketSelection


class DummySel:
    def __init__(self):
        self.selection_id = '1'
        self.name = 'Pocket Pair In Any Hand'
        self.status = 'IN_PLAY'
        self.best_back_price = 5.0


class TestBetManagerCommission(unittest.TestCase):
    def test_process_cleared_order_with_commission_and_profit(self):
        bm = BetManager(balance=100.0, max_exposure=50.0)
        sel = DummySel()
        opp = Opportunity(sel, true_prob=0.2, market_price=5.0, edge=0.1, action='BACK', stake=10.0)
        bet_id = '123'
        bm.record_accepted(bet_id, opp)
        # Simulate cleared order without explicit profit but with WON
        cleared = {'betId': bet_id, 'betOutcome': 'WON', 'commissionPaid': 0.5}
        profit = bm.process_cleared_order(cleared)
        # stake 10, payout = 10*(5-1)=40, commission 0.5 => net profit 39.5
        self.assertAlmostEqual(profit, 39.5)
        # Balance initially 100 - 10 = 90, after settlement + stake+payout - commission => 90 + 10 + 40 - 0.5 = 139.5
        self.assertAlmostEqual(bm.balance, 139.5)

    def test_process_cleared_order_with_reported_profit(self):
        bm = BetManager(balance=200.0, max_exposure=100.0)
        sel = DummySel()
        opp = Opportunity(sel, true_prob=0.2, market_price=3.0, edge=0.1, action='BACK', stake=20.0)
        bid = '456'
        bm.record_accepted(bid, opp)
        cleared = {'betId': bid, 'profit': 30.0, 'commissionPaid': 1.0}
        profit = bm.process_cleared_order(cleared)
        # profit should be 30 - 1 = 29
        self.assertAlmostEqual(profit, 29.0)
        # balance initial 200 - 20 = 180; + stake + profit - commission => 180 + 20 + 30 -1 = 229
        self.assertAlmostEqual(bm.balance, 229.0)


if __name__ == '__main__':
    unittest.main()
