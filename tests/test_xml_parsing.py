import unittest
from lxml import etree


class TestXMLParsing(unittest.TestCase):
    def test_parse_channel_snapshot(self):
        with open('tests/sample_channel_snapshot.xml', 'rb') as f:
            xml_content = f.read()
        try:
            root = etree.fromstring(xml_content)
            self.assertEqual(root.tag, 'channelSnapshot')
            shoe = root.find('shoe')
            self.assertIsNotNone(shoe)
            cards_dealt = int(shoe.find('cardsDealt').text)
            self.assertEqual(cards_dealt, 10)
            selections = root.find('marketSelections')
            self.assertIsNotNone(selections)
            selection = selections.find('selection')
            self.assertEqual(selection.find('name').text, 'Pocket Pair In Any Hand')
        except Exception as e:
            self.fail(f'XML parsing failed: {e}')


if __name__ == "__main__":
    unittest.main()
