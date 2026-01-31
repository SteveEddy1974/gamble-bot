import unittest
from unittest.mock import MagicMock
from models import MarketSelection, Opportunity
from executor import Executor


class TestExecutor(unittest.TestCase):
    def setUp(self):
        # Mock APIClient
        self.mock_api_client = MagicMock()
        self.executor = Executor(self.mock_api_client, currency="GBP")
        self.selection = MarketSelection(
            selection_id="1",
            name="Pocket Pair In Any Hand",
            status="IN_PLAY",
            best_back_price=5.0,
            best_lay_price=5.5
        )
        self.opportunity = Opportunity(
            selection=self.selection,
            true_prob=0.2,
            market_price=5.0,
            edge=0.1,
            action="BACK",
            stake=10.0
        )

    def test_place_bet_calls_api(self):
        self.executor.place_bet(
            market_id="123",
            round_id="456",
            opportunity=self.opportunity
        )
        self.mock_api_client.post_bet_order.assert_called_once_with(
            market_id="123",
            round_id="456",
            currency="GBP",
            bid_type="BACK",
            price=5.0,
            stake=10.0,
            selection_id="1",
        )


if __name__ == "__main__":
    unittest.main()
