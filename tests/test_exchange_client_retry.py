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
        if self.status_code != 200:
            raise Exception(f'status {self.status_code}')


class TestExchangeClientRetry(unittest.TestCase):
    def test_json_rpc_retries_on_429_503_and_succeeds(self):
        sequence = [DummyResp(503), DummyResp(429), DummyResp(200, {'result': {'foo': 'bar'}})]
        mock_session = Mock()
        mock_session.post = Mock(side_effect=sequence)
        client = ExchangeAPIClient('appkey', 'token', session=mock_session)
        result = client.json_rpc('method', {'x': 1}, request_id=42)
        self.assertIsInstance(result, dict)
        self.assertIn('result', result)
        self.assertEqual(result['result']['foo'], 'bar')
        # ensure post was called at least 3 times
        self.assertEqual(mock_session.post.call_count, 3)


if __name__ == '__main__':
    unittest.main()
