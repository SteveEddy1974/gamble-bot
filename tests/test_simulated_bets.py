import unittest
from api_client import SimulatedAPIClient
from executor import Executor
from models import MarketSelection, Opportunity


class TestSimulatedBets(unittest.TestCase):
    def test_place_simulated_bet(self):
        sim = SimulatedAPIClient()
        executor = Executor(sim, currency='GBP')
        sel = MarketSelection(
            selection_id='1',
            name='Pocket Pair In Any Hand',
            status='IN_PLAY',
            best_back_price=5.0,
            best_lay_price=5.5,
        )
        opp = Opportunity(
            selection=sel,
            true_prob=0.2,
            market_price=5.0,
            edge=0.1,
            action='BACK',
            stake=10.0,
        )
        resp = executor.place_bet('m1', 'r1', opp)
        status_el = resp.find('status') if resp is not None else None
        self.assertIsNotNone(status_el)
        self.assertEqual(status_el.text, 'ACCEPTED')


if __name__ == '__main__':
    unittest.main()
