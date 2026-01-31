import unittest
from main import BetManager
from models import MarketSelection, Opportunity


class TestBetManager(unittest.TestCase):
    def test_place_and_settle_win(self):
        bm = BetManager(balance=1000, max_exposure=100)
        sel = MarketSelection(
            selection_id='1',
            name='Pocket Pair In Any Hand',
            status='IN_PLAY',
            best_back_price=5.0,
            best_lay_price=5.5,
        )
        opp = Opportunity(
            selection=sel,
            true_prob=0.25,
            market_price=5.0,
            edge=0.2,
            action='BACK',
            stake=20.0,
        )
        # simulate accepted bet
        bm.record_accepted('b1', opp)
        self.assertEqual(bm.balance, 980.0)
        self.assertEqual(bm.current_exposure, 20.0)
        # settle as WON with payout stake*(price-1)=20*(4)=80
        profit = bm.process_settlement('b1', 'WON', 80.0)
        self.assertEqual(profit, 80.0)
        self.assertEqual(bm.balance, 1080.0)  # 980 + 20 + 80 (stake returned + payout)
        self.assertEqual(bm.current_exposure, 0.0)
        self.assertEqual(bm.pnl, 80.0)

    def test_place_and_settle_loss(self):
        bm = BetManager(balance=1000, max_exposure=100)
        sel = MarketSelection(
            selection_id='1',
            name='Pocket Pair In Any Hand',
            status='IN_PLAY',
            best_back_price=5.0,
            best_lay_price=5.5,
        )
        opp = Opportunity(
            selection=sel,
            true_prob=0.25,
            market_price=5.0,
            edge=0.2,
            action='BACK',
            stake=30.0,
        )
        bm.record_accepted('b2', opp)
        self.assertEqual(bm.balance, 970.0)
        self.assertEqual(bm.current_exposure, 30.0)
        profit = bm.process_settlement('b2', 'LOST', 0.0)
        self.assertEqual(profit, -30.0)
        self.assertEqual(bm.balance, 970.0)
        self.assertEqual(bm.current_exposure, 0.0)
        self.assertEqual(bm.pnl, -30.0)


if __name__ == '__main__':
    unittest.main()
