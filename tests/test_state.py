import unittest
import tempfile
import os
from state import load_state, save_state


class TestStatePersistence(unittest.TestCase):
    def test_save_and_load_state(self):
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.close()
        path = tmp.name
        try:
            state = {'last_cleared_timestamp': '2026-01-30T12:00:00Z', 'processed_bet_ids': ['1', '2']}
            save_state(path, state)
            loaded = load_state(path)
            self.assertEqual(loaded['last_cleared_timestamp'], state['last_cleared_timestamp'])
            self.assertEqual(loaded['processed_bet_ids'], state['processed_bet_ids'])
        finally:
            os.unlink(path)


if __name__ == '__main__':
    unittest.main()
