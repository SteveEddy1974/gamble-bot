import unittest
from engine import size_stake
from main import BetManager


class TestMinStakeBehavior(unittest.TestCase):
    def test_min_stake_applied_for_small_computed_stake(self):
        balance = 30.0
        max_exposure_pct = 0.1
        # Choose parameters that lead to small Kelly stake
        price = 2.0
        true_prob = 0.51
        # Use a very small shrink so computed stake is tiny
        computed = size_stake(balance, max_exposure_pct, edge=0.01, price=price, true_prob=true_prob, strategy='kelly', shrink=0.01)
        self.assertTrue(computed < 1.0)

        # Emulate main.py enforcement of min_stake
        min_stake = 1.0
        stake = computed
        if stake < min_stake:
            stake = min_stake
        # Check that stake is raised to min_stake and can be placed by BetManager
        self.assertEqual(stake, min_stake)
        bm = BetManager(balance=balance, max_exposure=balance * max_exposure_pct)
        self.assertTrue(bm.can_place(stake))


if __name__ == '__main__':
    unittest.main()
