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


class TestExchangeJsonRetryAndTimeout(unittest.TestCase):
    def test_json_rpc_retries_on_json_error_and_succeeds(self):
        # First call returns 200 but .json() raises, second returns valid json
        responses = []

        def first(*a, **k):
            r = Mock()
            r.status_code = 200
            r.json = Mock(side_effect=ValueError('Bad JSON'))
            return r

        def second(*a, **k):
            return DummyResp(200, {'result': {'ok': True}})

        mock_session = Mock()
        mock_session.post = Mock(side_effect=[first(), second()])
        client = ExchangeAPIClient('app', 'tkn', session=mock_session)
        res = client.json_rpc('Method', {'x': 1}, retry_on_json_error=True)
        self.assertIn('result', res)
        self.assertEqual(mock_session.post.call_count, 2)

    def test_json_rpc_does_not_retry_on_json_error_by_default(self):
        # Default behavior should not retry on JSON decode errors
        def bad(*a, **k):
            r = Mock()
            r.status_code = 200
            r.json = Mock(side_effect=ValueError('Bad JSON'))
            return r

        mock_session = Mock()
        mock_session.post = Mock(side_effect=[bad()])
        client = ExchangeAPIClient('app', 'tkn', session=mock_session)
        with self.assertRaises(ValueError):
            client.json_rpc('Method', {'x': 1})
        self.assertEqual(mock_session.post.call_count, 1)

    def test_json_rpc_passes_timeout_to_session_post(self):
        captured = {}

        def fake_post(url, data=None, timeout=None, **kwargs):
            captured['timeout'] = timeout
            r = Mock()
            r.status_code = 200
            r.json.return_value = {'result': {}}
            return r

        mock_session = Mock()
        mock_session.post = Mock(side_effect=fake_post)
        client = ExchangeAPIClient('app', 'tkn', session=mock_session)
        client.json_rpc('Method', {'x': 1}, timeout=3.5)
        self.assertIn('timeout', captured)
        self.assertEqual(captured['timeout'], 3.5)


if __name__ == '__main__':
    unittest.main()
