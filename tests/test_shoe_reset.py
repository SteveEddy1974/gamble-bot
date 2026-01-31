import unittest
from main import detect_shoe_reset


class TestShoeResetDetection(unittest.TestCase):
    def test_shoe_reset(self):
        # Simulate cardsRemaining history
        history = [200, 180, 160, 416]  # Jump to 416 = reset
        resets = [detect_shoe_reset(history[i - 1], history[i]) for i in range(1, len(history))]
        self.assertEqual(resets, [False, False, True])

    def test_no_reset(self):
        history = [416, 400, 380, 360]
        resets = [detect_shoe_reset(history[i - 1], history[i]) for i in range(1, len(history))]
        self.assertEqual(resets, [False, False, False])


if __name__ == "__main__":
    unittest.main()
