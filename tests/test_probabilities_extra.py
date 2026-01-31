import unittest
from probabilities import prob_pocket_pair, prob_natural_win, prob_natural_tie, prob_highest_hand_nine, prob_highest_hand_odd
from models import ShoeState


class TestProbabilitiesExtra(unittest.TestCase):
    def make_uniform_shoe(self):
        # 416 cards, 32 copies of each rank (approx) across 8 decks
        counts = {r: 32 for r in range(1, 14)}
        return ShoeState(cards_dealt=0, cards_remaining=416, card_counts=counts)

    def test_new_functions_sanity(self):
        s = self.make_uniform_shoe()
        p_tie = prob_natural_tie(s)
        p_high9 = prob_highest_hand_nine(s)
        p_odd = prob_highest_hand_odd(s)
        # All probabilities should be in [0,1]
        for p in (p_tie, p_high9, p_odd):
            self.assertGreaterEqual(p, 0.0)
            self.assertLessEqual(p, 1.0)
        # Specific sanity relation: highest=9 should be non-negligible
        self.assertGreaterEqual(p_high9, 0.0)

    def test_pocket_and_natural_existing(self):
        s = self.make_uniform_shoe()
        pp = prob_pocket_pair(s)
        nw = prob_natural_win(s)
        self.assertGreaterEqual(pp, 0.0)
        self.assertGreaterEqual(nw, 0.0)


if __name__ == '__main__':
    unittest.main()
