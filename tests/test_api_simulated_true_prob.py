import unittest
from api_client import SimulatedAPIClient


class TestSimulatedAPIClientTrueProb(unittest.TestCase):
    def test_post_bet_records_true_prob_and_returns_accepted(self):
        sim = SimulatedAPIClient(start_cards_remaining=416, decrement=4)
        # pull a snapshot to set internal state
        sim.get_snapshot('dummy')
        # Place a pocket pair (selection '1') bet
        resp = sim.post_bet_order('m', 'r', 'USD', 'BACK', price=5.0, stake=10.0, selection_id='1')
        status_el = resp.find('status')
        self.assertIsNotNone(status_el)
        self.assertEqual(status_el.text, 'ACCEPTED')
        bet_id_el = resp.find('betId')
        self.assertIsNotNone(bet_id_el)
        bet_id = bet_id_el.text
        self.assertIn(bet_id, sim.pending_bets)
        entry = sim.pending_bets[bet_id]
        self.assertIn('true_prob', entry)
        tp = entry['true_prob']
        self.assertGreaterEqual(tp, 0.0)
        self.assertLessEqual(tp, 1.0)


if __name__ == '__main__':
    unittest.main()
