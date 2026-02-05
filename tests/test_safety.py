import unittest
from main import BetManager, is_balance_sufficient_for_live


class TestSafetyChecks(unittest.TestCase):
    def test_balance_sufficient_for_live_true(self):
        cfg = {'bot': {'min_stake': 1.0}}
        bm = BetManager(balance=5.0, max_exposure=1.0)
        self.assertTrue(is_balance_sufficient_for_live(bm, cfg))

    def test_balance_sufficient_for_live_false(self):
        cfg = {'bot': {'min_stake': 1.0}}
        bm = BetManager(balance=0.5, max_exposure=1.0)
        self.assertFalse(is_balance_sufficient_for_live(bm, cfg))


if __name__ == '__main__':
    unittest.main()
