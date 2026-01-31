"""Simple alerting helper.

Currently supports sending a JSON POST to a configured webhook (one-way, best-effort).
"""
from typing import Dict, Any, Optional
import logging
import json

try:
    import requests
except Exception:
    requests = None


def send_alert(config: Dict[str, Any], message: str, level: str = 'WARNING') -> None:
    bot = config.get('bot', {})
    if not bot.get('alerts_enabled', False):
        logging.log(getattr(logging, level, logging.WARNING), 'Alert (disabled): %s', message)
        return
    webhook = bot.get('alert_webhook_url')
    if not webhook:
        logging.log(getattr(logging, level, logging.WARNING), 'Alert (no webhook): %s', message)
        return
    payload = {'level': level, 'message': message}
    if requests is None:
        logging.error('requests not available; cannot send alert: %s', message)
        return
    try:
        requests.post(webhook, json=payload, timeout=3)
    except Exception:
        logging.exception('Failed to send alert to %s: %s', webhook, message)
