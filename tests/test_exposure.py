import unittest
from engine import size_stake


class TestExposureSizing(unittest.TestCase):
    def test_size_stake_and_exposure_limit(self):
        balance = 1000
        max_exposure_pct = 0.1
        edges = [0.05, 0.05, 0.05]
        stakes = [size_stake(balance, max_exposure_pct, e) for e in edges]
        self.assertEqual(stakes[0], 50.0)
        self.assertEqual(stakes[1], 50.0)
        self.assertEqual(stakes[2], 50.0)
        max_exposure = balance * max_exposure_pct
        current_exposure = 0.0
        accepted = []
        for s in stakes:
            if current_exposure + s > max_exposure:
                accepted.append(False)
            else:
                current_exposure += s
                accepted.append(True)
        self.assertEqual(accepted, [True, True, False])
        self.assertEqual(current_exposure, 100.0)


if __name__ == '__main__':
    unittest.main()
