import os
import hashlib
import unittest

import operator_gate as op_mod


class TestOperator(unittest.TestCase):
    def test_operator_token_hash_matches(self):
        token = 'my-secret-token'
        h = hashlib.sha256(token.encode()).hexdigest()
        cfg = {'bot': {'operator_token_env': 'BOT_OPERATOR_TOKEN', 'operator_token_hash': h, 'live_enabled': True, 'simulate': False}}
        os.environ['BOT_OPERATOR_TOKEN'] = token
        try:
            self.assertTrue(op_mod.is_operator_enabled(cfg))
            self.assertTrue(op_mod.is_live_allowed(cfg))
        finally:
            del os.environ['BOT_OPERATOR_TOKEN']

    def test_operator_token_mismatch(self):
        token = 'my-secret-token'
        h = hashlib.sha256('other'.encode()).hexdigest()
        cfg = {'bot': {'operator_token_env': 'BOT_OPERATOR_TOKEN', 'operator_token_hash': h, 'live_enabled': True, 'simulate': False}}
        os.environ['BOT_OPERATOR_TOKEN'] = token
        try:
            self.assertFalse(op_mod.is_operator_enabled(cfg))
            self.assertFalse(op_mod.is_live_allowed(cfg))
        finally:
            del os.environ['BOT_OPERATOR_TOKEN']

    def test_simulate_blocks_live(self):
        cfg = {'bot': {'simulate': True, 'live_enabled': True}}
        self.assertFalse(op_mod.is_live_allowed(cfg))
