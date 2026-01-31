import json
from typing import Dict, Any
from pathlib import Path


def load_state(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {'last_cleared_timestamp': None, 'processed_bet_ids': []}
    try:
        with p.open('r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {'last_cleared_timestamp': None, 'processed_bet_ids': []}


def save_state(path: str, state: Dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('w', encoding='utf-8') as f:
        json.dump(state, f)
