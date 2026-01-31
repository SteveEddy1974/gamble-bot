import unittest
from engine import size_stake


class TestEngineKelly(unittest.TestCase):
    def test_kelly_stake_basic(self):
        balance = 1000
        price = 5.0
        true_prob = 0.25
        stake = size_stake(balance, 0.1, 0.2, price=price, true_prob=true_prob, strategy='kelly', shrink=0.5)
        # kelly f = (b*p - q)/b where b=4, p=0.25, q=0.75 -> f=(1 - 0.75)/4=0.0625, shrink 0.5 => 0.03125
        expected = balance * 0.03125
        self.assertAlmostEqual(stake, expected)

    def test_kelly_falls_back_to_proportional(self):
        stake = size_stake(1000, 0.1, 0.05, price=None, true_prob=None, strategy='kelly')
        self.assertGreaterEqual(stake, 0)


if __name__ == '__main__':
    unittest.main()
