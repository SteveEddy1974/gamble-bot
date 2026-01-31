from lxml import etree

import metrics
from executor import Executor
from main import BetManager
from models import Opportunity, MarketSelection


def make_opportunity():
    sel = MarketSelection(selection_id='1', name='Side', status='IN_PLAY', best_back_price=2.0, best_lay_price=None)
    # Opportunity signature: selection, true_prob, market_price, edge, action, stake
    return Opportunity(selection=sel, true_prob=0.5, market_price=2.0, edge=0.1, action='BACK', stake=1.0)


class DummyAPI_Post:
    def post_bet_order(self, **kwargs):
        resp = etree.Element('response')
        status = etree.SubElement(resp, 'status')
        status.text = 'ACCEPTED'
        return resp


class DummyAPI_PlaceOrders:
    def place_orders(self, market_id, instructions):
        return {'result': True}


import unittest


class TestMetricsIntegration(unittest.TestCase):
    def setUp(self) -> None:
        metrics._counters.clear()

    def test_executor_post_bet_increments_metrics(self):
        api = DummyAPI_Post()
        exe = Executor(api_client=api, currency='USD')
        opp = make_opportunity()
        exe.place_bet('m1', 'r1', opp)
        counters = metrics.get_counters()
        self.assertEqual(counters.get('bets_placed'), 1)
        self.assertEqual(counters.get('bets_accepted'), 1)

    def test_executor_place_orders_increments_metrics(self):
        api = DummyAPI_PlaceOrders()
        exe = Executor(api_client=api, currency='USD')
        opp = make_opportunity()
        exe.place_bet('m1', 'r1', opp)
        counters = metrics.get_counters()
        self.assertEqual(counters.get('bets_placed'), 1)
        self.assertEqual(counters.get('bets_accepted'), 1)

    def test_settlement_processing_increments_metrics(self):
        bm = BetManager(100.0, 100.0)
        # add an active bet
        bm.active_bets['bet-1'] = {'stake': 2.0}
        # process a win
        bm.process_settlement('bet-1', 'WON', payout=3.0)
        self.assertEqual(metrics.get_counters().get('settlements_processed'), 1)
        self.assertEqual(metrics.get_counters().get('settlement_wins'), 1)

        # add loss
        metrics._counters.clear()
        bm.active_bets['bet-2'] = {'stake': 1.0}
        bm.process_settlement('bet-2', 'LOST', payout=0.0)
        self.assertEqual(metrics.get_counters().get('settlements_processed'), 1)
        self.assertEqual(metrics.get_counters().get('settlement_losses'), 1
)

