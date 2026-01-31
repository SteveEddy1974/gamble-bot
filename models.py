from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class ShoeState:
    cards_dealt: int
    cards_remaining: int
    card_counts: Dict[int, int]  # 1=Ace, 11=J, 12=Q, 13=K


@dataclass
class MarketSelection:
    selection_id: str
    name: str  # e.g., "Pocket Pair In Any Hand"
    status: str  # "IN_PLAY", "LOSER", "WINNER"
    best_back_price: Optional[float]
    best_lay_price: Optional[float]


@dataclass
class Opportunity:
    selection: MarketSelection
    true_prob: float
    market_price: float
    edge: float
    action: str  # "BACK" or "LAY"
    stake: float
