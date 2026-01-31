import unittest
from models import ShoeState
from probabilities import (
    prob_pocket_pair,
    prob_natural_win,
)


class TestProbabilities(unittest.TestCase):
    def setUp(self):
        # Full shoe: 8 decks, 52 cards each
        self.full_shoe = ShoeState(
            cards_dealt=0,
            cards_remaining=416,
            card_counts={i: 32 for i in range(1, 14)}
        )

    def test_probabilities_sum(self):
        # Check functions return sane values for a full shoe
        pp = prob_pocket_pair(self.full_shoe)
        nw = prob_natural_win(self.full_shoe)
        # Basic sanity checks: probabilities in (0,1)
        self.assertGreater(pp, 0.0)
        self.assertLess(pp, 1.0)
        self.assertGreater(nw, 0.0)
        self.assertLess(nw, 1.0)
        # Pocket pair for one of two hands should be reasonably small (~0.05-0.25)
        self.assertGreater(pp, 0.02)
        self.assertLess(pp, 0.3)
        # Natural win empirical should be around 0.2-0.45
        self.assertGreater(nw, 0.1)
        self.assertLess(nw, 0.5)

    def test_additional_sidebets(self):
        from probabilities import prob_natural_tie, prob_highest_hand_nine, prob_highest_hand_odd
        tie = prob_natural_tie(self.full_shoe)
        high9 = prob_highest_hand_nine(self.full_shoe)
        high_odd = prob_highest_hand_odd(self.full_shoe)
        # Sanity checks
        self.assertGreaterEqual(tie, 0.0)
        self.assertLessEqual(tie, 1.0)
        self.assertGreaterEqual(high9, 0.0)
        self.assertLessEqual(high9, 1.0)
        self.assertGreaterEqual(high_odd, 0.0)
        self.assertLessEqual(high_odd, 1.0)
        # Natural tie should be small
        self.assertLess(tie, 0.1)
        # Highest 9 is more common than a natural tie (roughly), so check it's >= tie
        self.assertGreaterEqual(high9, tie)
        # Highest odd should be > 0
        self.assertGreater(high_odd, 0.0)


if __name__ == "__main__":
    unittest.main()
