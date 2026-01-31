import unittest
from engine import evaluate, size_stake, COMMISSION, MIN_EDGE


class TestEngineBehavior(unittest.TestCase):
    def test_evaluate_back_and_lay_edge(self):
        # BACK: true_prob high leads to positive edge
        ok, edge = evaluate(None, true_prob=0.5, market_price=2.0, action='BACK')
        # implied_prob = 1/2 = 0.5, edge = 0.5 - 0.5 - COMMISSION = -COMMISSION -> not OK
        self.assertFalse(ok)
        # If true_prob slightly higher
        ok2, edge2 = evaluate(None, true_prob=0.6, market_price=2.0, action='BACK')
        self.assertTrue(edge2 > MIN_EDGE)
        self.assertTrue(ok2)

        # LAY: when implied_prob is high and true_prob low, edge should be positive
        ok3, edge3 = evaluate(None, true_prob=0.1, market_price=1.5, action='LAY')
        # implied_prob = 1/1.5 = 0.666..., edge approx 0.666 - 0.1 - COMMISSION
        self.assertTrue(edge3 > MIN_EDGE)
        self.assertTrue(ok3)

    def test_size_stake_kelly_and_proportional(self):
        balance = 1000.0
        max_exposure_pct = 0.1
        # Kelly with sufficient inputs
        stake = size_stake(balance, max_exposure_pct, edge=0.2, price=5.0, true_prob=0.2, strategy='kelly', shrink=0.5)
        self.assertGreaterEqual(stake, 0.0)
        self.assertLessEqual(stake, balance * max_exposure_pct)

        # Kelly with missing inputs falls back to proportional
        stake2 = size_stake(balance, max_exposure_pct, edge=0.05, price=None, true_prob=None, strategy='kelly')
        self.assertGreaterEqual(stake2, 0.0)
        self.assertLessEqual(stake2, balance * max_exposure_pct)

        # proportional with tiny edge returns small or zero stake
        stake3 = size_stake(balance, max_exposure_pct, edge=0.0, strategy='proportional')
        self.assertEqual(stake3, 0.0)

        stake4 = size_stake(balance, max_exposure_pct, edge=0.05, strategy='proportional')
        self.assertGreaterEqual(stake4, 0.0)
        self.assertLessEqual(stake4, balance * max_exposure_pct)


if __name__ == '__main__':
    unittest.main()
