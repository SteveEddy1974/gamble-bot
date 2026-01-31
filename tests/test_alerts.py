import unittest

import alerts


class DummyResp:
    def __init__(self):
        self.called = True


def dummy_post(url, json=None, timeout=None):
    dummy_post.called = True
    dummy_post.url = url
    dummy_post.payload = json
    return DummyResp()


class TestAlerts(unittest.TestCase):
    def setUp(self):
        alerts.requests = type('R', (), {'post': staticmethod(dummy_post)})

    def tearDown(self):
        # restore real requests if available
        try:
            import requests
            alerts.requests = requests
        except Exception:
            alerts.requests = None

    def test_send_alert_posts_when_enabled(self):
        cfg = {'bot': {'alerts_enabled': True, 'alert_webhook_url': 'http://example.local/alert'}}
        alerts.send_alert(cfg, 'test-message', level='ERROR')
        self.assertTrue(getattr(dummy_post, 'called', False))
        self.assertEqual(dummy_post.url, 'http://example.local/alert')
        self.assertIn('test-message', dummy_post.payload.get('message', ''))

    def test_send_alert_logs_when_disabled(self):
        cfg = {'bot': {'alerts_enabled': False}}
        # should not raise
        alerts.send_alert(cfg, 'no-op')
