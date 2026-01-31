import time
import argparse
import logging
from typing import Any, Dict, Optional, List

import yaml

from api_client import APIClient, SimulatedAPIClient
from engine import evaluate, size_stake
from executor import Executor
from probabilities import prob_pocket_pair, prob_natural_win
from models import ShoeState, MarketSelection, Opportunity

CONFIG_PATH = "config.yaml"


def load_config() -> Dict[str, Any]:
    with open(CONFIG_PATH, 'r') as f:
        return yaml.safe_load(f)


def setup_logging(config: Dict[str, Any]) -> None:
    logging.basicConfig(
        filename=config['logging']['file'],
        level=getattr(logging, config['logging']['level']),
        format='%(asctime)s %(levelname)s %(message)s'
    )
    # If simulation is enabled, also log to console for easier observation
    try:
        if config.get('bot', {}).get('simulate', False):
            ch = logging.StreamHandler()
            ch.setLevel(getattr(logging, config['logging']['level']))
            ch.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
            logging.getLogger().addHandler(ch)
    except Exception:
        pass


def detect_shoe_reset(prev_cards_remaining: int, curr_cards_remaining: int, threshold: int = 400) -> bool:
    """
    Returns True if shoe reset is detected (cardsRemaining jumps to ~416)
    """
    return prev_cards_remaining < threshold and curr_cards_remaining >= 416


def parse_shoe_state(shoe_elem: Any) -> ShoeState:
    cards_dealt = int(shoe_elem.find('cardsDealt').text)
    cards_remaining = int(shoe_elem.find('cardsRemaining').text)
    card_counts: dict = {}
    for card in shoe_elem.find('cardCounts').findall('card'):
        rank = int(card.attrib['rank'])
        count = int(card.text)
        card_counts[rank] = count
    return ShoeState(cards_dealt, cards_remaining, card_counts)


def parse_market_selections(selections_elem: Any) -> List[MarketSelection]:
    selections: List[MarketSelection] = []
    for sel in selections_elem.findall('selection'):
        selection_id = sel.find('selectionId').text
        name = sel.find('name').text
        status = sel.find('status').text
        best_back_price = float(sel.find('bestBackPrice').text) if sel.find('bestBackPrice') is not None else None
        best_lay_price = float(sel.find('bestLayPrice').text) if sel.find('bestLayPrice') is not None else None
        selections.append(MarketSelection(selection_id, name, status, best_back_price, best_lay_price))
    return selections


class BetManager:
    def __init__(self, balance: float, max_exposure: float) -> None:
        self.balance: float = balance
        self.max_exposure: float = max_exposure
        self.current_exposure: float = 0.0
        self.active_bets: dict = {}  # betId -> {'opp': Opportunity, 'stake': float, 'price': float}
        self.pnl: float = 0.0
        self.trade_history: list = []

    def can_place(self, stake: float) -> bool:
        return (self.current_exposure + stake) <= self.max_exposure and stake <= self.balance

    def record_accepted(self, bet_id: str, opp: Opportunity) -> None:
        stake = opp.stake
        self.active_bets[bet_id] = {'opp': opp, 'stake': stake, 'price': opp.market_price}
        # Reserve stake from balance
        self.balance -= stake
        self.current_exposure += stake

    def process_settlement(self, bet_id: str, status: str, payout: float) -> Optional[float]:
        rec = self.active_bets.pop(bet_id, None)
        if rec is None:
            return None
        stake = rec['stake']
        if status == 'WON':
            # Return stake and payout
            self.balance += stake + payout
            profit = payout
        else:
            # stake already removed; loss = -stake
            profit = -stake
        self.current_exposure = max(0.0, self.current_exposure - stake)
        self.pnl += profit
        self.trade_history.append({'bet_id': bet_id, 'profit': profit, 'balance': self.balance})
        # Metrics: count settlements and wins/losses
        try:
            from metrics import inc_settlement_processed, inc_settlement_win, inc_settlement_loss
            inc_settlement_processed()
            if profit > 0:
                inc_settlement_win()
            else:
                inc_settlement_loss()
        except Exception:
            pass
        return profit

    def process_cleared_order(self, cleared: dict) -> Optional[float]:
        """Process a cleared order dict from Exchange API.
        Expected keys (common): 'betId', 'betOutcome' ('WON'|'LOST'), 'profit', 'commissionPaid'.
        """
        bet_id = str(cleared.get('betId'))
        rec = self.active_bets.pop(bet_id, None)
        if rec is None:
            return None
        stake = rec['stake']
        price = rec['price']
        # Prefer explicit profit from cleared order
        profit = None
        if 'profit' in cleared and cleared['profit'] is not None:
            profit = float(cleared['profit'])
            # When profit reported is net profit, return stake + profit
            self.balance += stake + profit
        else:
            outcome = cleared.get('betOutcome') or cleared.get('status')
            if outcome == 'WON':
                payout = stake * (price - 1.0)
                profit = payout
                self.balance += stake + payout
            else:
                profit = -stake
        # Subtract commission if present
        commission = float(cleared.get('commissionPaid', 0.0) or 0.0)
        if commission:
            self.balance -= commission
            profit -= commission
        self.current_exposure = max(0.0, self.current_exposure - stake)
        self.pnl += profit
        self.trade_history.append({'bet_id': bet_id, 'profit': profit, 'balance': self.balance})
        return profit


def reconcile_cleared_orders(
    api_client: Any,
    bet_manager: BetManager,
    state: Dict[str, Any],
    state_file: str,
    from_iso: Optional[str] = None,
    lookback: int = 3600,
    max_processed: int = 10000,
    csv_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Query Exchange API for cleared orders since from_iso (ISO 8601) or state['last_cleared_timestamp'].

    Deduplicate using state['processed_bet_ids'], save updated state to state_file, optionally append cleared
    orders to csv_path. Returns updated state.
    """
    from datetime import datetime, timezone, timedelta
    from state import save_state
    import csv
    import os

    now = datetime.now(timezone.utc)
    if from_iso is None:
        from_iso = state.get('last_cleared_timestamp')
    if from_iso is None:
        from_dt = now - timedelta(seconds=lookback)
    else:
        try:
            from_dt = datetime.fromisoformat(from_iso.rstrip('Z')).replace(tzinfo=timezone.utc)
        except Exception:
            from_dt = now - timedelta(seconds=lookback)
    to_dt = now
    params = {'settledDateRange': {'from': from_dt.isoformat(), 'to': to_dt.isoformat()}, 'betStatus': 'SETTLED'}
    res = api_client.list_cleared_orders(**params)
    cleared = res.get('result', {}).get('clearedOrders', []) if isinstance(res, dict) else []
    max_ts = None
    processed_list = state.get('processed_bet_ids', []) or []
    processed_set = set(processed_list)

    # Prepare CSV file if requested
    if csv_path:
        csv_exists = os.path.exists(csv_path)
        csv_file = open(csv_path, 'a', newline='', encoding='utf-8')
        csv_writer = csv.writer(csv_file)
        if not csv_exists:
            csv_writer.writerow(['betId', 'settledDate', 'betOutcome', 'profit', 'commission', 'raw'])
    else:
        csv_file = None
        csv_writer = None

    try:
        for c in cleared:
            bet_id = str(c.get('betId'))
            if bet_id in processed_set:
                continue
            # process each cleared order
            bet_manager.process_cleared_order(c)
            processed_list.append(bet_id)
            processed_set.add(bet_id)
            # CSV row
            if csv_writer:
                settled = c.get('settledDate') or c.get('settled') or c.get('settledDateUtc')
                profit = c.get('profit') if 'profit' in c else None
                commission = c.get('commissionPaid') if 'commissionPaid' in c else None
                row = [
                    bet_id,
                    settled,
                    c.get('betOutcome') or c.get('status'),
                    profit,
                    commission,
                    str(c),
                ]
                csv_writer.writerow(row)
            settled = c.get('settledDate') or c.get('settled') or c.get('settledDateUtc')
            if settled:
                # normalize iso
                try:
                    st = datetime.fromisoformat(settled.rstrip('Z')).replace(tzinfo=timezone.utc)
                    if max_ts is None or st > max_ts:
                        max_ts = st
                except Exception:
                    pass
            # Metrics: count processed settlements
            try:
                from metrics import inc_settlement_processed, inc_settlement_win, inc_settlement_loss
                inc_settlement_processed()
                outcome = c.get('betOutcome') or c.get('status')
                profit = None
                if 'profit' in c and c.get('profit') is not None:
                    profit = float(c.get('profit'))
                else:
                    outcome = c.get('betOutcome') or c.get('status')
                    if outcome == 'WON':
                        try:
                            # try to compute payout if needed
                            stake = None
                            # skip computing stake here; best-effort only
                            pass
                        except Exception:
                            pass
                    # profit may remain None
                if profit is not None:
                    if profit > 0:
                        inc_settlement_win()
                    else:
                        inc_settlement_loss()
            except Exception:
                pass
        # trim processed_list to max_processed if >0
        if max_processed and max_processed > 0 and len(processed_list) > max_processed:
            processed_list = processed_list[-max_processed:]
        if max_ts:
            state['last_cleared_timestamp'] = max_ts.isoformat()
        state['processed_bet_ids'] = processed_list
        save_state(state_file, state)
    finally:
        if csv_file:
            csv_file.close()
    return state


def main(iterations: Optional[int] = None, override_poll_interval: Optional[float] = None) -> None:
    config = load_config()
    setup_logging(config)
    # Use simulated client when enabled in config for dry testing
    if config.get('bot', {}).get('simulate', False):
        api_client = SimulatedAPIClient(
            start_cards_remaining=config['bot'].get('simulate_start_cards', 416),
            decrement=config['bot'].get('simulate_decrement', 4),
            reset_after=config['bot'].get('simulate_reset_after')
        )
    else:
        api_client = APIClient(config['credentials'])
    executor = Executor(api_client, config['bot']['currency'])
    min_edge = config['bot']['min_edge']
    poll_interval = (
        override_poll_interval
        if override_poll_interval is not None
        else config['bot']['poll_interval_seconds']
    )
    last_cards_remaining = None
    channel_id = config.get('bot', {}).get('channel_id', 'dummy_channel')
    market_id = config.get('bot', {}).get('market_id', 'dummy_market')
    round_id = 'dummy_round'  # Should be parsed from snapshot

    # Exposure and balance
    balance = config['bot'].get('start_balance', 1000)
    max_exposure = balance * config['bot'].get('max_exposure_pct', 0.1)

    bet_manager = BetManager(balance, max_exposure)
    # Start metrics server when enabled in config
    try:
        if config.get('bot', {}).get('metrics_enabled', False):
            # If prometheus integration is enabled, use it (binds to localhost)
            if config.get('bot', {}).get('metrics_prometheus', False):
                from metrics import start_prometheus_server
                port = config.get('bot', {}).get('metrics_prometheus_port', None)
                try:
                    used_port = start_prometheus_server(port)
                    logging.info('Started Prometheus metrics server on port %s', used_port)
                except Exception:
                    logging.exception('Unable to start Prometheus metrics server')
            else:
                from metrics import MetricsServer
                port = config.get('bot', {}).get('metrics_port', 8000)
                metrics_server = MetricsServer(port=port)
                metrics_server.start()
    except Exception:
        pass

    loops = 0
    while iterations is None or loops < iterations:
        try:
            xml_root = api_client.get_snapshot(channel_id)
            shoe_elem = xml_root.find('shoe')
            selections_elem = xml_root.find('marketSelections')
            shoe = parse_shoe_state(shoe_elem)
            selections = parse_market_selections(selections_elem)

            # Shoe reset detection
            if last_cards_remaining is not None and detect_shoe_reset(last_cards_remaining, shoe.cards_remaining):
                logging.info('Shoe reset detected!')
            last_cards_remaining = shoe.cards_remaining

            # Process settlements if present
            settlements_elem = xml_root.find('settlements')
            if settlements_elem is not None:
                for s in settlements_elem.findall('settlement'):
                    bet_id = s.find('betId').text if s.find('betId') is not None else None
                    selection_id = s.find('selectionId').text if s.find('selectionId') is not None else None
                    status = s.find('status').text if s.find('status') is not None else None
                    payout = float(s.find('payout').text) if s.find('payout') is not None else 0.0
                    logging.info(
                        'Settlement received: betId=%s selection=%s status=%s payout=%s',
                        bet_id,
                        selection_id,
                        status,
                        payout,
                    )
                    # Precise settlement handling via BetManager
                    if bet_id is not None:
                        profit = bet_manager.process_settlement(bet_id, status, payout)
                        logging.info(
                            'Processed settlement: betId=%s profit=%s balance=%s exposure=%s',
                            bet_id,
                            profit,
                            bet_manager.balance,
                            bet_manager.current_exposure,
                        )
                    else:
                        logging.warning('Settlement without betId; cannot process precisely')

                    # Periodic reconciliation via Exchange API for cleared orders
            if config['bot'].get('use_exchange_api', False):
                now = time.time()
                last = locals().get('last_cleared_poll', 0)
                if now - last >= config['bot'].get('exchange_poll_cleared_seconds', 60):
                    try:
                        # Incremental reconciliation using settledDateRange
                        lookback = config['bot'].get('exchange_cleared_lookback_seconds', 3600)
                        # Load state file and pass into reconcile
                        from state import load_state
                        state_file = config['bot'].get('state_file', 'state.json')
                        state = load_state(state_file)
                        state = reconcile_cleared_orders(
                            api_client,
                            bet_manager,
                            state,
                            state_file,
                            from_iso=None,
                            lookback=lookback,
                            csv_path=config['bot'].get('cleared_orders_csv'),
                        )
                    except Exception as e:
                        logging.error(f'Error reconciling cleared orders: {e}')
                    last_cleared_poll = now

            # Evaluate opportunities for Pocket Pair and Natural Win
            for sel in selections:
                if sel.status != 'IN_PLAY':
                    continue
                if sel.name == 'Pocket Pair In Any Hand' and sel.best_back_price:
                    prob = prob_pocket_pair(shoe)
                    ok, edge = evaluate(sel, prob, sel.best_back_price, 'BACK')
                    if ok:
                        stake = size_stake(
                            bet_manager.balance,
                            config['bot']['max_exposure_pct'],
                            edge,
                            price=sel.best_back_price,
                            true_prob=prob,
                        )
                        if not bet_manager.can_place(stake):
                            msg = (
                                'Skipping Pocket Pair opportunity due to exposure/balance limits: '
                                f'stake={stake} exposure={bet_manager.current_exposure}/{bet_manager.max_exposure} balance={bet_manager.balance}'
                            )
                            logging.warning(msg)
                            try:
                                from alerts import send_alert
                                send_alert(config, msg, level='WARNING')
                            except Exception:
                                pass
                        else:
                            opp = Opportunity(sel, prob, sel.best_back_price, edge, 'BACK', stake)
                            logging.info('Opportunity: %s', opp)

                            def _handle_response(resp, is_live=False):
                                status_el = resp.find('status') if resp is not None else None
                                status = status_el.text if status_el is not None else str(resp)
                                logging.info('Placed %s bet: status=%s', 'live' if is_live else 'simulated', status)
                                if status == 'ACCEPTED':
                                    bet_id_el = resp.find('betId')
                                    bet_id = bet_id_el.text if bet_id_el is not None else None
                                    if bet_id:
                                        bet_manager.record_accepted(bet_id, opp)
                                        logging.info('Bet recorded: betId=%s stake=%s', bet_id, stake)
                                        logging.info(
                                            'Exposure after placement: %s/%s Balance: %s',
                                            bet_manager.current_exposure,
                                            bet_manager.max_exposure,
                                            bet_manager.balance,
                                        )
                                        try:
                                            from metrics import inc_bet_accepted
                                            inc_bet_accepted()
                                        except Exception:
                                            pass
                                    else:
                                        logging.warning('Accepted bet without betId; cannot track precisely')

                            if config['bot'].get('simulate_place_bets', False):
                                try:
                                    resp = executor.place_bet(market_id, round_id, opp)
                                    _handle_response(resp, is_live=False)
                                except Exception as e:
                                    logging.error('Error placing simulated bet: %s', e)
                            else:
                                # Live: require operator token and explicit live_enabled
                                try:
                                    from operator_gate import is_live_allowed
                                    if not is_live_allowed(config):
                                        logging.warning('Live betting is disabled by operator gating; skipping placement')
                                        try:
                                            from alerts import send_alert
                                            send_alert(config, 'Live betting attempt blocked by gating', level='WARNING')
                                        except Exception:
                                            pass
                                    else:
                                        try:
                                            resp = executor.place_bet(market_id, round_id, opp)
                                            _handle_response(resp, is_live=True)
                                        except Exception as e:
                                            logging.error('Error placing live bet: %s', e)
                                except Exception:
                                    logging.exception('Error checking operator gating')
                if sel.name == 'Natural Win' and sel.best_back_price:
                    prob = prob_natural_win(shoe)
                    ok, edge = evaluate(sel, prob, sel.best_back_price, 'BACK')
                    if ok:
                        stake = size_stake(
                            bet_manager.balance,
                            config['bot']['max_exposure_pct'],
                            edge,
                            price=sel.best_back_price,
                            true_prob=prob,
                        )
                        if not bet_manager.can_place(stake):
                            msg = (
                                'Skipping Natural Win opportunity due to exposure/balance limits: '
                                f'stake={stake} exposure={bet_manager.current_exposure}/{bet_manager.max_exposure} balance={bet_manager.balance}'
                            )
                            logging.warning(msg)
                            try:
                                from alerts import send_alert
                                send_alert(config, msg, level='WARNING')
                            except Exception:
                                pass
                        else:
                            opp = Opportunity(sel, prob, sel.best_back_price, edge, 'BACK', stake)
                            logging.info('Opportunity: %s', opp)
                            if config['bot'].get('simulate_place_bets', False):
                                try:
                                    resp = executor.place_bet(market_id, round_id, opp)
                                    status_el = resp.find('status') if resp is not None else None
                                    status = status_el.text if status_el is not None else str(resp)
                                    logging.info('Placed simulated bet: status=%s', status)
                                    if status == 'ACCEPTED':
                                        bet_id_el = resp.find('betId')
                                        bet_id = bet_id_el.text if bet_id_el is not None else None
                                        if bet_id:
                                            bet_manager.record_accepted(bet_id, opp)
                                            logging.info('Bet recorded: betId=%s stake=%s', bet_id, stake)
                                            logging.info(
                                                'Exposure after placement: %s/%s Balance: %s',
                                                bet_manager.current_exposure,
                                                bet_manager.max_exposure,
                                                bet_manager.balance,
                                            )
                                            try:
                                                from metrics import inc_bet_accepted
                                                inc_bet_accepted()
                                            except Exception:
                                                pass
                                        else:
                                            logging.warning('Accepted bet without betId; cannot track precisely')
                                except Exception as e:
                                    logging.error('Error placing simulated bet: %s', e)
                            else:
                                # Live placement is gated — operator must explicitly enable and supply token
                                try:
                                    from operator_gate import is_live_allowed
                                    if not is_live_allowed(config):
                                        logging.warning('Live betting is disabled by operator gating; skipping placement')
                                        try:
                                            from alerts import send_alert
                                            send_alert(config, 'Live betting attempt blocked by gating', level='WARNING')
                                        except Exception:
                                            pass
                                    else:
                                        logging.info('Operator gating passed. Live placement is supported but disabled by default in this canary flow.')
                                except Exception:
                                    logging.exception('Error checking operator gating')
        except Exception as e:
            logging.error(f'Error in main loop: {e}')
        time.sleep(poll_interval)
        loops += 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Baccarat SideBets Bot')
    parser.add_argument('--iterations', type=int, default=None, help='Number of polling iterations to run (dry run)')
    parser.add_argument('--poll-interval', type=float, default=None, help='Override poll interval in seconds')
    args = parser.parse_args()
    main(iterations=args.iterations, override_poll_interval=args.poll_interval)
