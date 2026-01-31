import unittest
import threading
import time

from main import main


class TestSmokeCanary(unittest.TestCase):
    def test_short_simulation_runs(self):
        # Run a very short simulation loop to ensure main runs end-to-end
        # Use a separate thread to avoid blocking test runner
        t = threading.Thread(target=main, kwargs={'iterations': 2, 'override_poll_interval': 0.01})
        t.start()
        t.join(timeout=5)
        # thread should finish quickly
        self.assertFalse(t.is_alive(), 'main did not exit in time')
