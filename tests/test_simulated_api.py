import unittest
from api_client import SimulatedAPIClient


class TestSimulatedAPIClient(unittest.TestCase):
    def test_snapshot_progression_and_reset(self):
        sim = SimulatedAPIClient(start_cards_remaining=416, decrement=50, reset_after=2)
        snap1 = sim.get_snapshot('chan')
        cr1 = int(snap1.find('shoe').find('cardsRemaining').text)
        self.assertEqual(cr1, 366)
        # Check counts sum to cardsRemaining
        counts = [int(c.text) for c in snap1.find('shoe').find('cardCounts').findall('card')]
        self.assertEqual(sum(counts), cr1)
        snap2 = sim.get_snapshot('chan')
        cr2 = int(snap2.find('shoe').find('cardsRemaining').text)
        self.assertEqual(cr2, 316)
        counts2 = [int(c.text) for c in snap2.find('shoe').find('cardCounts').findall('card')]
        self.assertEqual(sum(counts2), cr2)
        # reset on third call since reset_after=2
        snap3 = sim.get_snapshot('chan')
        cr3 = int(snap3.find('shoe').find('cardsRemaining').text)
        self.assertEqual(cr3, 416)
        counts3 = [int(c.text) for c in snap3.find('shoe').find('cardCounts').findall('card')]
        self.assertEqual(sum(counts3), cr3)


if __name__ == '__main__':
    unittest.main()
