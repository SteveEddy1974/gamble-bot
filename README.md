# Baccarat SideBets Bot

[![CI](https://github.com/<OWNER>/<REPO>/actions/workflows/ci.yml/badge.svg)](https://github.com/<OWNER>/<REPO>/actions/workflows/ci.yml)  [![Codecov](https://codecov.io/gh/<OWNER>/<REPO>/branch/main/graph/badge.svg)](https://codecov.io/gh/<OWNER>/<REPO>)

**Note:** Replace `<OWNER>/<REPO>` with your GitHub repository path to enable badges.

**CI:** GitHub Actions workflow runs tests, linting and security scans; coverage is uploaded to Codecov when `CODECOV_TOKEN` is set.

Quickstart

- Install dependencies: `pip install -r requirements.txt`
- Run tests: `python -m unittest discover -v`
- Run the bot in simulation: `python main.py --iterations 10 --poll-interval 0.2` (ensure `config.yaml` has `simulate: true`)

## Metrics & Prometheus 📊

- The bot has an optional metrics exporter for canary and staging monitoring.
- Enable metrics in `config.yaml` under `bot:` with `metrics_enabled: true` and choose Prometheus via `metrics_prometheus: true`.
- By default the Prometheus server binds to localhost on an ephemeral port (`metrics_prometheus_port: null`). To use a fixed port, set `metrics_prometheus_port: 9100` (or another unused port).
- The CI workflow validates both the plain `/metrics` exporter and the Prometheus WSGI endpoint on each push to ensure metrics remain exposed.

Security note: the Prometheus server binds to `127.0.0.1` by default for safety; if you expose it externally, protect it with network ACLs or an internal gateway.

### Canary quick-start 🚀

- Run a short simulated canary (safe, does not place live bets):

  `python -m main --iterations 10 --poll-interval 0.5`

- Verify metrics endpoints:
  - HTTP exporter: `http://127.0.0.1:8000/metrics`
  - Prometheus WSGI:  `http://127.0.0.1:9151/metrics`

- To enable a gated live canary (operator-gated and with safe defaults):
  1. Generate a token and hash: `python scripts/generate_operator_token_hash.py <secret>` and set `BOT_OPERATOR_TOKEN` in your environment.
  2. In `config.yaml` set `bot.live_enabled: true` and `bot.operator_token_hash` to the generated hash.
  3. Verify `bot.use_exchange_api` is configured correctly (it is disabled by default for safety).

- The CI contains smoke checks that validate metrics endpoints and the Prometheus WSGI exporter to ensure observability during canary runs.

