import unittest
from unittest.mock import Mock
from api_client import ExchangeAPIClient


class TestExchangeAPIClientPlaceAndList(unittest.TestCase):
    def test_place_orders_and_list_market_book_call_json_rpc(self):
        # Mock session to return 200 and a simple json from post
        mock_session = Mock()
        resp = Mock()
        resp.status_code = 200
        resp.json.return_value = {'result': {'status': 'OK'}}
        mock_session.post.return_value = resp
        client = ExchangeAPIClient('akey', 'token', session=mock_session)
        r1 = client.place_orders('mkt', [{'dummy': 1}], customer_ref='ref')
        self.assertIn('result', r1)
        r2 = client.list_market_book(['m1'])
        self.assertIn('result', r2)
        # ensure session.post called
        self.assertTrue(mock_session.post.called)


if __name__ == '__main__':
    unittest.main()
