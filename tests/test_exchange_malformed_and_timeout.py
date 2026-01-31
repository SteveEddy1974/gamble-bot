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


class TestExchangeMalformedAndTimeout(unittest.TestCase):
    def test_json_rpc_raises_on_malformed_json_no_retry(self):
        # Server returns 200 but JSON decoding raises -> should bubble up and not retry
        def fake_post(url, data=None, **kwargs):
            r = Mock()
            r.status_code = 200
            r.json = Mock(side_effect=ValueError('Malformed JSON'))
            return r

        mock_session = Mock()
        mock_session.post = Mock(side_effect=fake_post)
        client = ExchangeAPIClient('app', 'tkn', session=mock_session)
        with self.assertRaises(ValueError):
            client.json_rpc('Method', {'x': 1})
        self.assertEqual(mock_session.post.call_count, 1)

    def test_json_rpc_retries_on_timeout_and_succeeds(self):
        # Simulate Timeout twice, then success
        seq = [requests.exceptions.Timeout(), requests.exceptions.Timeout(), DummyResp(200, {'result': {'ok': True}})]

        def side_effect(*a, **k):
            v = seq.pop(0)
            if isinstance(v, Exception):
                raise v
            return v

        mock_session = Mock()
        mock_session.post = Mock(side_effect=side_effect)
        client = ExchangeAPIClient('app', 'tkn', session=mock_session)
        res = client.json_rpc('Method', {'x': 1})
        self.assertIn('result', res)
        self.assertEqual(mock_session.post.call_count, 3)


if __name__ == '__main__':
    unittest.main()
