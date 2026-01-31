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

