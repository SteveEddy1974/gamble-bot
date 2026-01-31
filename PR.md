Branch: feature/exchange-retries-and-tests

Title: Harden Exchange JSON-RPC + add edge-case tests and CI coverage guard

Summary:
- Add timeout parameter and optional JSON-decoding retry to ExchangeAPIClient.json_rpc.
- Treat transient network exceptions (Timeout/ConnectionError) as retryable (existing behavior preserved).
- Add focused tests for JSON decode retry, malformed JSON, timeouts, and network exceptions.
- Add CI workflow to fail when coverage < 90%.
- Add small type-annotation updates to `main.py` for clarity and testability.

Test plan:
- Run full unit test suite: `python -m unittest discover` (all tests should pass).
- Run coverage: `coverage run -m unittest discover && coverage report --fail-under=90`.

Notes:
- This workspace is not a git repo here; to create a branch and open a PR locally:
  git checkout -b feature/exchange-retries-and-tests
  git add .
  git commit -m "Harden Exchange JSON-RPC + add edge-case tests and CI coverage guard"
  git push origin feature/exchange-retries-and-tests
  (Open a PR from the pushed branch with the above title/body.)
