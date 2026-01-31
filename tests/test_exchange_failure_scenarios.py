import unittest
from unittest.mock import Mock
from api_client import ExchangeAPIClient


class DummyResp:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        raise Exception(f'status {self.status_code}')


class TestExchangeFailureScenarios(unittest.TestCase):
    def test_json_rpc_raises_after_retry_exhaustion(self):
        # All attempts return 503 -> should eventually raise
        seq = [DummyResp(503), DummyResp(503), DummyResp(503)]
        mock_session = Mock()
        mock_session.post = Mock(side_effect=seq)
        client = ExchangeAPIClient('app', 'tkn', session=mock_session)
        with self.assertRaises(Exception):
            client.json_rpc('SomeMethod', {'x': 1})
        self.assertEqual(mock_session.post.call_count, 3)

    def test_json_rpc_raises_immediately_on_client_error(self):
        # Client error (400) should call raise_for_status immediately and not retry
        mock_session = Mock()
        mock_session.post = Mock(return_value=DummyResp(400))
        client = ExchangeAPIClient('app', 'tkn', session=mock_session)
        with self.assertRaises(Exception):
            client.json_rpc('SomeMethod', {'x': 1})
        self.assertEqual(mock_session.post.call_count, 1)

    def test_list_cleared_orders_sends_correct_method_and_params(self):
        # Capture data payload to ensure method and params forwarded
        captured = {}

        def fake_post(url, data=None, **kwargs):
            captured['data'] = data
            # return successful response
            r = Mock()
            r.status_code = 200
            r.json.return_value = {'result': {'clearedOrders': []}}
            return r

        mock_session = Mock()
        mock_session.post = Mock(side_effect=fake_post)
        client = ExchangeAPIClient('app', 'tkn', session=mock_session)
        params = {'settledDateRange': {'from': 'a', 'to': 'b'}, 'betStatus': 'SETTLED'}
        client.list_cleared_orders(**params)
        # Inspect JSON payload to ensure method is for listClearedOrders
        import json
        payload = json.loads(captured['data'])
        self.assertIn('method', payload)
        self.assertEqual(payload['method'], 'AccountAPING/v1.0/listClearedOrders')
        self.assertEqual(payload['params'], params)


if __name__ == '__main__':
    unittest.main()
