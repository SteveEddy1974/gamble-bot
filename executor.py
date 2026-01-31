from typing import Any, Dict, List
from api_client import APIClient
from models import Opportunity


class Executor:
    def __init__(self, api_client: Any, currency: str) -> None:
        self.api_client = api_client
        self.currency = currency

    def place_bet(self, market_id: str, round_id: str, opportunity: Opportunity) -> Dict[str, Any]:
        # Support both Games API (XML post_bet_order) and Exchange API (place_orders)
        # Prefer post_bet_order when present (backwards compatible), otherwise use place_orders
        from metrics import inc_bet_placed, inc_bet_accepted
        inc_bet_placed()
        if hasattr(self.api_client, 'post_bet_order'):
            resp = self.api_client.post_bet_order(
                market_id=market_id,
                round_id=round_id,
                currency=self.currency,
                bid_type=opportunity.action,
                price=opportunity.market_price,
                stake=opportunity.stake,
                selection_id=opportunity.selection.selection_id
            )
            status_el = resp.find('status') if resp is not None else None
            status = status_el.text if status_el is not None else str(resp)
            if status == 'ACCEPTED':
                inc_bet_accepted()
            return resp
        elif hasattr(self.api_client, 'place_orders'):
            # Build placeOrders instruction
            instruction = {
                'selectionId': int(opportunity.selection.selection_id),
                'handicap': 0,
                'side': 'BACK' if opportunity.action == 'BACK' else 'LAY',
                'orderType': 'LIMIT',
                'limitOrder': {
                    'price': opportunity.market_price,
                    'size': opportunity.stake,
                    'persistenceType': 'LAPSE'
                }
            }
            resp = self.api_client.place_orders(market_id, [instruction])
            # Try to detect success response
            try:
                if isinstance(resp, dict) and resp.get('result'):
                    inc_bet_accepted()
            except Exception:
                pass
            return resp
        else:
            raise RuntimeError('API client does not support post_bet_order or place_orders')
