import unittest
from unittest.mock import Mock
import requests
from api_client import ExchangeAPIClient


class DummyResp:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        raise Exception(f'status {self.status_code}')


class TestExchangeNetworkExceptions(unittest.TestCase):
    def test_json_rpc_retries_on_connection_error_and_succeeds(self):
        # Simulate ConnectionError twice, then success
        calls = [requests.exceptions.ConnectionError(), requests.exceptions.ConnectionError(), DummyResp(200, {'result': {'ok': True}})]
        def side_effect(*a, **k):
            v = calls.pop(0)
            if isinstance(v, Exception):
                raise v
            return v
        mock_session = Mock()
        mock_session.post = Mock(side_effect=side_effect)
        client = ExchangeAPIClient('app', 'tkn', session=mock_session)
        res = client.json_rpc('Method', {'x': 1})
        self.assertIn('result', res)
        self.assertEqual(mock_session.post.call_count, 3)

    def test_json_rpc_raises_after_connection_error_exhaustion(self):
        # Always raise ConnectionError
        mock_session = Mock()
        mock_session.post = Mock(side_effect=requests.exceptions.ConnectionError())
        client = ExchangeAPIClient('app', 'tkn', session=mock_session)
        with self.assertRaises(Exception):
            client.json_rpc('Method', {'x': 1})
        self.assertEqual(mock_session.post.call_count, 3)


if __name__ == '__main__':
    unittest.main()
