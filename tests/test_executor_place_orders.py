import unittest
from unittest.mock import MagicMock
from models import MarketSelection, Opportunity
from executor import Executor


class TestExecutorPlaceOrders(unittest.TestCase):
    def test_place_orders_branch_calls_place_orders(self):
        # Build an api client that lacks post_bet_order but has place_orders
        class DummyAPI:
            def __init__(self):
                self_place = self

            def place_orders(self, market_id, instructions):
                return {'status': 'OK', 'placed': len(instructions)}

        api = DummyAPI()
        executor = Executor(api, currency='USD')
        selection = MarketSelection('2', 'Natural Win', 'IN_PLAY', 3.0, 3.4)
        opp = Opportunity(selection, true_prob=0.1, market_price=3.0, edge=0.05, action='BACK', stake=5.0)
        resp = executor.place_bet('mkt', 'rnd', opp)
        self.assertIsInstance(resp, dict)
        self.assertEqual(resp.get('status'), 'OK')


if __name__ == '__main__':
    unittest.main()
