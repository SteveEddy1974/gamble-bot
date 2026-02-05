import requests
import hashlib
import logging
from lxml import etree
from typing import Any, Dict, Optional
import time
import json
import random
from datetime import datetime


class APIClient:
    """
    Client for Betfair Games API (per official v1.142 User Guide).

    Authentication uses three HTTP headers:
    - gamexAPIPassword: plaintext password (HTTPS encrypts connection)
    - gamexAPIAgent: application ID (e.g., email.AppName.Version)
    - gamexAPIAgentInstance: unique 32-char MD5 hash per installation

    Note: Games API is free to use, no API keys required.
    For Exchange API betting, use ExchangeAPIClient instead.
    """
    BASE_URL = "https://api.games.betfair.com/rest/v1"

    def __init__(self, credentials: Dict[str, str]):
        self.credentials = credentials
        self.session = requests.Session()
        self._set_auth_headers()

    def _generate_agent_instance_id(self) -> str:
        """
        Generate unique gamexAPIAgentInstance per official spec:
        1. Current timestamp in ISO format
        2. Append 5-digit random number
        3. Append gamexAPIAgent ID
        4. Return MD5 hash of combined string
        """
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        random_num = random.randint(10000, 99999)
        agent_id = self.session.headers.get('gamexAPIAgent', 'unknown')
        combined = f"{timestamp}{random_num}{agent_id}"
        return hashlib.md5(combined.encode()).hexdigest()

    def _set_auth_headers(self):
        username = (self.credentials or {}).get('username')
        password = (self.credentials or {}).get('password')
        if not username or not password:
            raise ValueError(
                "Missing Betfair credentials. Set BETFAIR_USERNAME/BETFAIR_PASSWORD env vars "
                "or populate credentials in config.yaml."
            )

        # Per official guide: gamexAPIAgent format is email.AppName.Version
        agent_id = f"{username}.BaccaratBot.1.0"

        # Set headers per official spec (plaintext password, proper agent format)
        self.session.headers.update({
            'gamexAPIPassword': password,  # Plaintext (HTTPS encrypts)
            'gamexAPIAgent': agent_id
        })

        # Generate unique instance ID after agent is set
        instance_id = self._generate_agent_instance_id()
        self.session.headers.update({
            'gamexAPIAgentInstance': instance_id
        })

    def get_snapshot(self, channel_id: str, selections_type: Optional[str] = None) -> Any:
        # Per official spec: must include username in URL query parameter
        username = self.credentials.get('username')
        url = f"{self.BASE_URL}/channels/{channel_id}/snapshot?username={username}"
        if selections_type:
            url = f"{url}&selectionsType={selections_type}"
        resp = self.session.get(url)
        resp.raise_for_status()
        return etree.fromstring(resp.content)

    def post_bet_order(
        self,
        market_id: str,
        round_id: str,
        currency: str,
        bid_type: str,
        price: float,
        stake: float,
        selection_id: str,
    ) -> Any:
        # Build XML payload per official spec
        payload = f'''
        <postBetOrder xmlns="urn:betfair:games:api:v1" marketId="{market_id}" round="{round_id}" currency="{currency}">
          <totalSizeRequest>
            <bidType>{bid_type}</bidType>
            <price>{price}</price>
            <totalSize>{stake}</totalSize>
            <selectionId>{selection_id}</selectionId>
          </totalSizeRequest>
        </postBetOrder>
        '''
        # Per official spec: include username in URL
        username = self.credentials.get('username')
        url = f"{self.BASE_URL}/bet/order?username={username}"
        resp = self.session.post(url, data=payload, headers={'Content-Type': 'application/xml'})
        try:
            resp.raise_for_status()
        except Exception as e:
            request_body = None
            try:
                request_body = resp.request.body
                if isinstance(request_body, bytes):
                    request_body = request_body.decode('utf-8', errors='replace')
            except Exception:
                request_body = '<unavailable>'

            response_text = resp.text
            if response_text and len(response_text) > 2000:
                response_text = response_text[:2000] + '...'

            logging.error(
                'POST /bet/order failed: status=%s url=%s request_body=%s response=%s',
                resp.status_code,
                url,
                request_body,
                response_text,
            )
            raise RuntimeError(
                f'Bet order failed: status={resp.status_code} response={response_text}'
            ) from e
        return etree.fromstring(resp.content)


class SimulatedAPIClient:
    """Simple simulator that returns generated channelSnapshot XML for testing."""

    def __init__(
        self,
        start_cards_remaining: int = 416,
        decrement: int = 4,
        reset_after: int = None,
        settle_delay: int = 2,
    ):
        self.start_cards_remaining = start_cards_remaining
        self.cards_remaining = start_cards_remaining
        self.decrement = decrement
        self.reset_after = reset_after
        self.iteration = 0
        self.settle_delay = settle_delay
        # Initialize card counts proportional to start_cards_remaining
        decks = start_cards_remaining / 52.0
        self.card_counts = {r: max(0, int(round(4 * decks))) for r in range(1, 14)}
        # Pending bets: betId -> info dict
        self.pending_bets = {}
        self._next_bet_id = 1

    def _generate_snapshot(self):
        # Build counts xml from current internal counts
        counts = [
            f'<card rank="{r}">{self.card_counts.get(r, 0)}</card>'
            for r in range(1, 14)
        ]
        counts_xml = ''.join(counts)

        # Vary prices slightly based on counts (simple heuristic)
        # Add random inefficiency to create betting opportunities
        import random
        pocket_pressure = max(0, (self.card_counts[1] - 28) / 32)
        # Base price with wider inefficiency range to create 5%+ edges
        pocket_inefficiency = random.uniform(0.4, 1.4)  # Wider range for bigger mispricings
        pocket_price = round(5.0 * pocket_inefficiency + (self.iteration % 3) * 0.1 - pocket_pressure * 0.2, 3)
        
        natural_pressure = max(0, (self.card_counts[8] + self.card_counts[9] - 60) / 64)
        natural_inefficiency = random.uniform(0.4, 1.4)
        natural_price = round(3.0 * natural_inefficiency + (self.iteration % 5) * 0.05 - natural_pressure * 0.1, 3)

        # If any bets are due for settlement, produce settlement XML entries
        settlements = []
        to_settle = []
        for bet_id, b in list(self.pending_bets.items()):
            if self.iteration - b['placed_iteration'] >= self.settle_delay:
                import random
                won = random.random() < b.get('true_prob', 0.0)
                payout = 0.0
                if won:
                    payout = round(b['stake'] * (b['price'] - 1.0), 2)
                status = 'WON' if won else 'LOST'
                settlements.append((bet_id, b.get('selectionId'), status, payout))
                to_settle.append(bet_id)
        for bid in to_settle:
            del self.pending_bets[bid]

        parts = []
        for bid, sel, status, payout in settlements:
            parts.append(
                '<settlement>'
                f'<betId>{bid}</betId>'
                f'<selectionId>{sel}</selectionId>'
                f'<status>{status}</status>'
                f'<payout>{payout}</payout>'
                '</settlement>'
            )
        settlements_xml = ''.join(parts)

        xml_parts = [
            '<channelSnapshot>',
            '  <shoe>',
            f'    <cardsDealt>{416 - self.cards_remaining}</cardsDealt>',
            f'    <cardsRemaining>{self.cards_remaining}</cardsRemaining>',
            '    <cardCounts>',
            counts_xml,
            '    </cardCounts>',
            '  </shoe>',
            '  <marketSelections>',
            '    <selection>',
            '      <selectionId>1</selectionId>',
            '      <name>Pocket Pair In Any Hand</name>',
            '      <status>IN_PLAY</status>',
            f'      <bestBackPrice>{pocket_price}</bestBackPrice>',
            f'      <bestLayPrice>{pocket_price + 0.5}</bestLayPrice>',
            '    </selection>',
            '    <selection>',
            '      <selectionId>2</selectionId>',
            '      <name>Natural Win</name>',
            '      <status>IN_PLAY</status>',
            f'      <bestBackPrice>{natural_price}</bestBackPrice>',
            f'      <bestLayPrice>{natural_price + 0.4}</bestLayPrice>',
            '    </selection>',
            '  </marketSelections>',
            '  <settlements>',
            settlements_xml,
            '  </settlements>',
            '</channelSnapshot>',
        ]
        xml = '\n'.join(xml_parts)
        return xml.encode("utf-8")

    def get_snapshot(self, channel_id: str, selections_type: Optional[str] = None) -> Any:
        # On each call, decrement cards_remaining and simulate reset
        if self.reset_after and self.iteration > 0 and self.iteration % self.reset_after == 0:
            # Reset shoe every reset_after iterations (return a full shoe snapshot on reset)
            self.cards_remaining = self.start_cards_remaining if hasattr(self, 'start_cards_remaining') else 416
            # reset card counts
            decks = self.cards_remaining / 52.0
            self.card_counts = {
                r: max(0, int(round(4 * decks)))
                for r in range(1, 14)
            }
            # Return a full snapshot immediately on reset without decrementing
            xml = self._generate_snapshot()
            self._current_raw_snapshot = xml
            self.iteration += 1
            return etree.fromstring(xml)
        
        if self.cards_remaining > 0:
            # Decrease card counts in a round-robin way to simulate dealing
            to_remove = self.decrement
            r = (self.iteration % 13) + 1
            attempts = 0
            max_attempts = 13  # One full cycle through all ranks
            while to_remove > 0 and attempts < max_attempts:
                if self.card_counts.get(r, 0) > 0:
                    self.card_counts[r] -= 1
                    to_remove -= 1
                    attempts = 0  # Reset attempts when we successfully remove a card
                else:
                    attempts += 1
                r = r % 13 + 1
            # Decrease but don't go below 0
            self.cards_remaining = max(0, self.cards_remaining - self.decrement)
        xml = self._generate_snapshot()
        self._current_raw_snapshot = xml
        self.iteration += 1
        return etree.fromstring(xml)

    def _current_shoe_state(self):
        # Helper to return a ShoeState for current internal counts
        from models import ShoeState
        cards_dealt = 416 - self.cards_remaining
        cards_remaining = self.cards_remaining
        return ShoeState(
            cards_dealt=cards_dealt,
            cards_remaining=cards_remaining,
            card_counts=self.card_counts.copy(),
        )

    def post_bet_order(
        self,
        market_id: str,
        round_id: str,
        currency: str,
        bid_type: str,
        price: float,
        stake: float,
        selection_id: str,
    ) -> Any:
        # Record pending bet and return response with betId
        bet_id = str(self._next_bet_id)
        self._next_bet_id += 1
        # Compute true probability for selection at time of bet
        try:
            if selection_id == '1' or selection_id == 'Pocket Pair In Any Hand':
                from probabilities import prob_pocket_pair
                true_prob = prob_pocket_pair(self._current_shoe_state())
            elif selection_id == '2' or selection_id == 'Natural Win':
                from probabilities import prob_natural_win
                true_prob = prob_natural_win(self._current_shoe_state())
            else:
                true_prob = 1.0 / price
        except Exception:
            true_prob = 1.0 / price
        self.pending_bets[bet_id] = {
            'betId': bet_id,
            'selectionId': selection_id,
            'price': price,
            'stake': stake,
            'placed_iteration': self.iteration,
            'true_prob': true_prob,
            'status': 'PENDING'
        }
        resp_parts = [
            '<postBetOrderResponse>',
            '<status>ACCEPTED</status>',
            f'<selectionId>{selection_id}</selectionId>',
            f'<betId>{bet_id}</betId>',
            '</postBetOrderResponse>',
        ]
        resp = ''.join(resp_parts)
        return etree.fromstring(resp.encode('utf-8'))


class ExchangeAPIClient:
    """Lightweight JSON-RPC client for Betfair Exchange API (for placeOrders, listMarketBook, listClearedOrders)."""

    JSON_RPC_URL = "https://api.betfair.com/exchange/betting/json-rpc/v1"

    def __init__(self, app_key: str, session_token: str, session: Optional[requests.Session] = None):
        self.app_key = app_key
        self.session_token = session_token
        self.session = session or requests.Session()
        self.session.headers.update({
            'X-Application': self.app_key,
            'X-Authentication': self.session_token,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })

    def json_rpc(
        self,
        method: str,
        params: dict,
        request_id: int = 1,
        timeout: float | None = None,
        retry_on_json_error: bool = False,
    ):
        payload = json.dumps({
            'jsonrpc': '2.0',
            'method': method,
            'params': params,
            'id': request_id
        })
        # Basic retry/backoff, treat network exceptions as retryable
        for attempt in range(3):
            try:
                resp = self.session.post(self.JSON_RPC_URL, data=payload, timeout=timeout)
            except Exception:
                # Retry on transient network errors
                if attempt < 2:
                    from metrics import inc_exchange_rpc_retry
                    inc_exchange_rpc_retry(method)
                    time.sleep(0.5 * (attempt + 1))
                    continue
                from metrics import inc_exchange_rpc_error
                inc_exchange_rpc_error(method)
                raise
            if resp.status_code == 200:
                # Parse JSON, optionally retry on JSON decode errors
                try:
                    return resp.json()
                except ValueError:
                    if retry_on_json_error and attempt < 2:
                        from metrics import inc_exchange_rpc_retry
                        inc_exchange_rpc_retry(method)
                        time.sleep(0.5 * (attempt + 1))
                        continue
                    from metrics import inc_exchange_rpc_error
                    inc_exchange_rpc_error(method)
                    raise
            elif resp.status_code in (429, 503):
                from metrics import inc_exchange_rpc_retry
                inc_exchange_rpc_retry(method)
                time.sleep(0.5 * (attempt + 1))
                continue
            else:
                resp.raise_for_status()
        resp.raise_for_status()

    def list_market_book(self, market_ids, price_projection=None):
        params = {'marketIds': market_ids}
        if price_projection is not None:
            params['priceProjection'] = price_projection
        return self.json_rpc('SportsAPING/v1.0/listMarketBook', params)

    def place_orders(self, market_id: str, instructions: list, customer_ref: Optional[str] = None):
        params = {'marketId': market_id, 'instructions': instructions}
        if customer_ref:
            params['customerRef'] = customer_ref
        return self.json_rpc('SportsAPING/v1.0/placeOrders', params)

    def list_cleared_orders(self, **kwargs):
        # kwargs can include settledDateRange, betStatus, etc.
        params = kwargs
        return self.json_rpc('AccountAPING/v1.0/listClearedOrders', params)
