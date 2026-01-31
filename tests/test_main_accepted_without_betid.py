import unittest
import tempfile
import yaml
import os
from lxml import etree
import main


class DummySimNoBetId:
    def __init__(self, *a, **k):
        pass

    def get_snapshot(self, channel_id):
        xml = '''
        <channelSnapshot>
          <shoe>
            <cardsDealt>0</cardsDealt>
            <cardsRemaining>416</cardsRemaining>
            <cardCounts>
              <card rank="1">32</card>
            </cardCounts>
          </shoe>
          <marketSelections>
            <selection>
              <selectionId>1</selectionId>
              <name>Pocket Pair In Any Hand</name>
              <status>IN_PLAY</status>
              <bestBackPrice>5.0</bestBackPrice>
            </selection>
          </marketSelections>
          <settlements></settlements>
        </channelSnapshot>
        '''
        return etree.fromstring(xml.encode('utf-8'))

    def post_bet_order(self, *a, **k):
        resp = '<postBetOrderResponse><status>ACCEPTED</status></postBetOrderResponse>'
        return etree.fromstring(resp.encode('utf-8'))


class TestMainAcceptedNoBetId(unittest.TestCase):
    def test_main_handles_accepted_without_betid_gracefully(self):
        tmp_cfg = tempfile.NamedTemporaryFile(delete=False, suffix='.yaml')
        tmp_cfg.close()
        cfg = {
            'credentials': {'username': '', 'password': ''},
            'bot': {
                'min_edge': 0.0,
                'max_exposure_pct': 0.1,
                'start_balance': 1000,
                'poll_interval_seconds': 0.01,
                'currency': 'GBP',
                'simulate': True,
                'simulate_place_bets': True,
                'simulate_start_cards': 416,
                'simulate_decrement': 4,
                'simulate_reset_after': None,
                'state_file': tmp_cfg.name,
            },
            'logging': {'level': 'INFO', 'file': 'bot.log'}
        }
        with open(tmp_cfg.name, 'w', encoding='utf-8') as f:
            yaml.safe_dump(cfg, f)
        old = main.CONFIG_PATH
        main.CONFIG_PATH = tmp_cfg.name
        old_sim = main.SimulatedAPIClient
        main.SimulatedAPIClient = DummySimNoBetId
        try:
            main.main(iterations=1, override_poll_interval=0.01)
        finally:
            main.CONFIG_PATH = old
            main.SimulatedAPIClient = old_sim
            os.unlink(tmp_cfg.name)


if __name__ == '__main__':
    unittest.main()
