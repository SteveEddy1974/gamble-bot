from lxml import etree
from scripts.dry_run_real_api import _selection_records
from main import parse_shoe_state, parse_market_selections
root = etree.fromstring(open('tests/sample_channel_snapshot.xml','rb').read())
ns = {'bf': 'urn:betfair:games:api:v1'}
shoe_elem = root.find('.//bf:shoe', ns) or root.find('.//shoe')
selections_elem = root.find('.//bf:marketSelections', ns) or root.find('.//marketSelections')
shoe = parse_shoe_state(shoe_elem)
selections = parse_market_selections(selections_elem)
print('Shoe.cards_remaining=', shoe.cards_remaining)
print('Selections=', [(s.name,s.status,s.best_back_price) for s in selections])
print('Records=', _selection_records(selections, shoe))
