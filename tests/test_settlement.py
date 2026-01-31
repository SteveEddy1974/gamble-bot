import unittest
from api_client import SimulatedAPIClient


class TestSettlementSimulation(unittest.TestCase):
    def test_bet_settlement_occurs(self):
        sim = SimulatedAPIClient(start_cards_remaining=416, decrement=4, reset_after=None, settle_delay=1)
        # Place a bet
        resp = sim.post_bet_order('m1', 'r1', 'GBP', 'BACK', 5.0, 10.0, '1')
        bet_id = resp.find('betId').text
        self.assertIn(bet_id, sim.pending_bets)
        # Next snapshot may not settle immediately; call twice since settle_delay=1
        snap = sim.get_snapshot('chan')
        snap = sim.get_snapshot('chan')
        settlements = snap.find('settlements')
        found = False
        for s in settlements.findall('settlement'):
            if s.find('betId').text == bet_id:
                found = True
                # payout present
                self.assertIsNotNone(s.find('payout'))
        self.assertTrue(found)
        # Pending bet removed
        self.assertNotIn(bet_id, sim.pending_bets)


if __name__ == '__main__':
    unittest.main()
