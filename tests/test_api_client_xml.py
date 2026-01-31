import unittest
from api_client import APIClient


class DummyResp:
    def __init__(self, content, status_code=200):
        self.content = content
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f'Status {self.status_code}')


class TestAPIClientXML(unittest.TestCase):
    def setUp(self):
        self.creds = {'username': 'u', 'password': 'p'}
        self.client = APIClient(self.creds)

    def test_get_snapshot_parses_xml(self):
        xml = b"""
<channelSnapshot>
  <shoe>
    <cardsDealt>5</cardsDealt>
    <cardsRemaining>411</cardsRemaining>
    <cardCounts>
      <card rank=\"1\">32</card>
    </cardCounts>
  </shoe>
  <marketSelections></marketSelections>
</channelSnapshot>
"""
        self.client.session.get = lambda url: DummyResp(xml, status_code=200)
        root = self.client.get_snapshot('chan')
        self.assertEqual(root.tag, 'channelSnapshot')

    def test_post_bet_order_returns_xml(self):
        resp_xml = b"<postBetOrderResponse><status>ACCEPTED</status><betId>123</betId></postBetOrderResponse>"
        self.client.session.post = lambda url, data, headers: DummyResp(resp_xml, status_code=200)
        resp = self.client.post_bet_order('m', 'r', 'GBP', 'BACK', 5.0, 10.0, '1')
        self.assertEqual(resp.find('status').text, 'ACCEPTED')
        self.assertEqual(resp.find('betId').text, '123')


if __name__ == '__main__':
    unittest.main()
