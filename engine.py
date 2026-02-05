from typing import Any, List, Tuple

COMMISSION = 0.025
MIN_EDGE = 0.05  # Default threshold


def evaluate(selection: Any, true_prob: float, market_price: float, action: str, min_edge: float = MIN_EDGE) -> Tuple[bool, float]:
    implied_prob = 1.0 / market_price
    if action == "BACK":
        edge = true_prob - implied_prob - COMMISSION
        return edge > min_edge, edge
    if action == "LAY":
        edge = implied_prob - true_prob - COMMISSION
        return edge > min_edge, edge
    return False, 0.0


def rank_opportunities(opportunities):
    # TODO: Sort and filter by edge
    return sorted(opportunities, key=lambda o: o.edge, reverse=True)


def calculate_dynamic_max_stake_pct(balance: float) -> float:
    """Calculate dynamic max stake percentage based on bankroll size.
    
    - Balance < £100: 3% (conservative for small bankrolls)
    - Balance £100-200: 4% (moderate as bankroll grows)
    - Balance > £200: 5% (more aggressive for larger bankrolls)
    """
    if balance < 100:
        return 0.03
    elif balance < 200:
        return 0.04
    else:
        return 0.05


def size_stake(balance, max_exposure_pct, edge, price=None, true_prob=None, strategy='kelly', shrink=0.25, max_stake_pct=0.10):
    """Size stake using selected strategy (kelly or proportional).

    Returned stake is capped at both max_exposure_pct * balance and max_stake_pct * balance.

    - Kelly: uses f = (b * p - q) / b where b = price - 1, p = true_prob, q = 1 - p. Apply shrink factor.
    - proportional: stake = balance * max_exposure_pct * min(1, edge / 0.1)
    """
    cap = balance * max_exposure_pct
    max_single_stake = balance * max_stake_pct
    if strategy == 'kelly':
        if price is None or true_prob is None:
            # fallback to proportional if missing inputs
            return size_stake(balance, max_exposure_pct, edge, strategy='proportional')
        b = max(0.0, price - 1.0)
        p = true_prob
        q = 1.0 - p
        if b <= 0:
            return 0.0
        f = (b * p - q) / b
        f = max(0.0, f)
        f = f * shrink
        stake = balance * f
        return min(stake, cap, max_single_stake)
    # proportional
    if edge <= 0:
        return 0.0
    scale = min(1.0, edge / 0.1)
    return min(balance * max_exposure_pct * scale, cap, max_single_stake)
