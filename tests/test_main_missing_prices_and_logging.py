import unittest
import logging
from lxml import etree
from main import parse_market_selections, setup_logging


class TestMainMissingPricesAndLogging(unittest.TestCase):
    def test_parse_market_selection_missing_prices(self):
        xml = '''
        <marketSelections>
          <selection>
            <selectionId>3</selectionId>
            <name>Other Bet</name>
            <status>IN_PLAY</status>
          </selection>
        </marketSelections>
        '''
        root = etree.fromstring(xml.encode('utf-8'))
        sels = parse_market_selections(root)
        self.assertEqual(len(sels), 1)
        s = sels[0]
        self.assertIsNone(s.best_back_price)
        self.assertIsNone(s.best_lay_price)

    def test_setup_logging_no_console_when_not_simulate(self):
        cfg = {'logging': {'file': 'test.log', 'level': 'INFO'}, 'bot': {'simulate': False}}
        # Before count
        before = len(logging.getLogger().handlers)
        setup_logging(cfg)
        after = len(logging.getLogger().handlers)
        # No new StreamHandler should be added
        self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()
