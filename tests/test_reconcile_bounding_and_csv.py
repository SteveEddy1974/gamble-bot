import unittest
import tempfile
import os
from unittest.mock import MagicMock
from main import reconcile_cleared_orders
from main import BetManager


class TestReconcileBoundingCSV(unittest.TestCase):
    def test_bounding_of_processed_ids_and_csv_logging(self):
        tmp_state = tempfile.NamedTemporaryFile(delete=False)
        tmp_state.close()
        tmp_csv = tempfile.NamedTemporaryFile(delete=False)
        tmp_csv.close()
        try:
            mock_api = MagicMock()
            # generate 5 cleared orders
            cleared = []
            for i in range(1, 6):
                cleared.append(
                    {
                        'betId': str(i),
                        'profit': float(i * 2),
                        'commissionPaid': 0.0,
                        'settledDate': f'2026-01-30T12:0{i}:00Z',
                        'betOutcome': 'WON',
                    }
                )
            mock_api.list_cleared_orders.return_value = {'result': {'clearedOrders': cleared}}

            bm = BetManager(balance=1000, max_exposure=100)
            # pre-record bets 1..5
            for i in range(1, 6):
                opp = MagicMock()
                opp.stake = 10.0
                opp.market_price = 2.0
                bm.record_accepted(str(i), opp)

            state = {'last_cleared_timestamp': None, 'processed_bet_ids': []}
            # max_processed = 3
            state = reconcile_cleared_orders(
                mock_api,
                bm,
                state,
                tmp_state.name,
                from_iso=None,
                lookback=3600,
                max_processed=3,
                csv_path=tmp_csv.name,
            )
            self.assertEqual(len(state['processed_bet_ids']), 3)
            # Ensure csv file has header + 3 rows
            with open(tmp_csv.name, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            self.assertGreaterEqual(len(lines), 4)
        finally:
            os.unlink(tmp_state.name)
            os.unlink(tmp_csv.name)


if __name__ == '__main__':
    unittest.main()
