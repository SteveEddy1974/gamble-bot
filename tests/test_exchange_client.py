import unittest
from unittest.mock import MagicMock
from api_client import ExchangeAPIClient


class TestExchangeAPIClient(unittest.TestCase):
    def test_json_rpc_success(self):
        mock_sess = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {'result': 'ok'}
        mock_sess.post.return_value = mock_resp
        client = ExchangeAPIClient('app', 'token', session=mock_sess)
        res = client.json_rpc('Some/method', {'k': 'v'})
        self.assertEqual(res, {'result': 'ok'})
        mock_sess.post.assert_called()

    def test_place_orders_builds_request(self):
        mock_sess = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {'result': {'instructionReports': []}}
        mock_sess.post.return_value = mock_resp
        client = ExchangeAPIClient('app', 'token', session=mock_sess)
        r = client.place_orders('1.2', [{'selectionId': 1, 'handicap': 0}])
        self.assertIn('result', r)
        mock_sess.post.assert_called()


if __name__ == '__main__':
    unittest.main()
