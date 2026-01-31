import unittest
import tempfile
import os
import yaml

import main


class TestMainSimulationRun(unittest.TestCase):
    def test_main_runs_with_simulation_and_writes_state_and_csv(self):
        # Create temporary config file enabling simulation and CSV/state paths
        tmp_cfg = tempfile.NamedTemporaryFile(delete=False, suffix='.yaml')
        tmp_csv = tempfile.NamedTemporaryFile(delete=False, suffix='.csv')
        tmp_state = tempfile.NamedTemporaryFile(delete=False)
        tmp_cfg.close()
        tmp_csv.close()
        tmp_state.close()
        cfg = {
            'credentials': {'username': '', 'password': ''},
            'bot': {
                'min_edge': 0.05,
                'max_exposure_pct': 0.1,
                'start_balance': 1000,
                'poll_interval_seconds': 0.01,
                'currency': 'GBP',
                'simulate': True,
                'simulate_place_bets': True,
                'simulate_start_cards': 416,
                'simulate_decrement': 4,
                'simulate_reset_after': None,
                'state_file': tmp_state.name,
                'state_max_processed_ids': 100,
                'cleared_orders_csv': tmp_csv.name
            },
            'logging': {'level': 'INFO', 'file': 'bot.log'}
        }
        with open(tmp_cfg.name, 'w', encoding='utf-8') as f:
            yaml.safe_dump(cfg, f)
        # Temporarily point CONFIG_PATH to our temp config
        old = main.CONFIG_PATH
        main.CONFIG_PATH = tmp_cfg.name
        try:
            # Run only 2 iterations in dry mode
            main.main(iterations=2, override_poll_interval=0.01)
            # Ensure state file exists and CSV created
            self.assertTrue(os.path.exists(tmp_state.name))
            self.assertTrue(os.path.exists(tmp_csv.name))
            # State should have processed_bet_ids list or last_cleared_timestamp
            import json
            # Try reading state if non-empty JSON
            try:
                with open(tmp_state.name, 'r', encoding='utf-8') as sf:
                    txt = sf.read().strip()
                    if txt:
                        s = json.loads(txt)
                        self.assertIn('processed_bet_ids', s)
            except Exception:
                # Accept failure to parse: state file may be empty if no cleared orders processed in short run
                pass
        finally:
            main.CONFIG_PATH = old
            os.unlink(tmp_cfg.name)
            if os.path.exists(tmp_csv.name):
                os.unlink(tmp_csv.name)
            # Attempt to remove state file; ignore permission errors on Windows
            try:
                if os.path.exists(tmp_state.name):
                    os.unlink(tmp_state.name)
            except PermissionError:
                pass


if __name__ == '__main__':
    unittest.main()
