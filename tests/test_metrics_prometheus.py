import unittest
import requests

import metrics


try:
    from prometheus_client import Counter  # type: ignore
    PROM_AVAILABLE = True
except Exception:
    PROM_AVAILABLE = False


@unittest.skipUnless(PROM_AVAILABLE, "prometheus_client not installed")
class TestPrometheusIntegration(unittest.TestCase):
    def setUp(self) -> None:
        metrics._counters.clear()

    def test_prometheus_server_exposes_metrics(self):
        # start prometheus server on ephemeral port
        port = metrics.start_prometheus_server(port=None)
        try:
            metrics.inc_bet_placed()
            # give server a moment
            import time
            time.sleep(0.05)
            r = requests.get(f'http://127.0.0.1:{port}/', timeout=2)
            self.assertEqual(r.status_code, 200)
            text = r.text
            self.assertIn('bets_placed', text)
        finally:
            metrics.stop_prometheus_server()
