"""Operator gating helpers for canary/live enablement."""
import os
import hashlib
from typing import Dict, Any


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


def is_operator_enabled(config: Dict[str, Any]) -> bool:
    bot = config.get('bot', {})
    token_env = bot.get('operator_token_env', 'BOT_OPERATOR_TOKEN')
    token_hash = bot.get('operator_token_hash')
    if not token_hash:
        return False
    token = os.getenv(token_env)
    if not token:
        return False
    return _sha256_hex(token) == token_hash


def is_live_allowed(config: Dict[str, Any]) -> bool:
    bot = config.get('bot', {})
    if bot.get('simulate', False):
        return False
    if not bot.get('live_enabled', False):
        return False
    return is_operator_enabled(config)
