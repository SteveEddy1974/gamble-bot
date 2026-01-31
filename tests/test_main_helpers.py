import unittest
import logging
import tempfile
import os
from main import setup_logging, load_config, parse_market_selections, parse_shoe_state, detect_shoe_reset
from lxml import etree


class TestMainHelpers(unittest.TestCase):
    def test_setup_logging_simulate_adds_console_handler(self):
        cfg = {'logging': {'file': 'test.log', 'level': 'INFO'}, 'bot': {'simulate': True}}
        # Ensure no exception and handler added
        setup_logging(cfg)
        handlers = logging.getLogger().handlers
        self.assertTrue(any(isinstance(h, logging.StreamHandler) for h in handlers))

    def test_load_config_reads_yaml(self):
        cfg = load_config()
        self.assertIn('bot', cfg)
        self.assertIn('logging', cfg)

    def test_parse_market_and_shoe(self):
        xml = '''
        <channelSnapshot>
          <shoe>
            <cardsDealt>0</cardsDealt>
            <cardsRemaining>416</cardsRemaining>
            <cardCounts>
              <card rank="1">32</card>
              <card rank="2">32</card>
            </cardCounts>
          </shoe>
          <marketSelections>
            <selection>
              <selectionId>1</selectionId>
              <name>Pocket Pair In Any Hand</name>
              <status>IN_PLAY</status>
              <bestBackPrice>4.0</bestBackPrice>
            </selection>
          </marketSelections>
        </channelSnapshot>
        '''
        root = etree.fromstring(xml.encode('utf-8'))
        shoe = root.find('shoe')
        selections = root.find('marketSelections')
        s = parse_shoe_state(shoe)
        self.assertEqual(s.cards_remaining, 416)
        sel = parse_market_selections(selections)
        self.assertEqual(len(sel), 1)

    def test_detect_shoe_reset_threshold(self):
        self.assertTrue(detect_shoe_reset(300, 416))
        self.assertFalse(detect_shoe_reset(410, 415))


if __name__ == '__main__':
    unittest.main()
