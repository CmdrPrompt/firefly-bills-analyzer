# firefly-python-api

Python client library for the [Firefly III](https://www.firefly-iii.org/) REST API.

Provides a shared HTTP layer with credential management and API coverage for
accounts, transactions, and reporting resources. Designed to be used as a
dependency by consumer projects such as `firefly-bank-importer` and
`firefly-bills-analyzer`.

## Features

- `FireflyClient(url, token)` — authenticated `requests.Session` with correct
  headers wired up automatically
- `load_config(env_path)` — reads `FIREFLY_URL` and `FIREFLY_TOKEN` from
  environment or a `.env` file
- `FireflyClient.validate_connection()` — probes `/api/v1/about` and raises
  `FireflyConnectionError` on failure
- Account methods: `get_asset_accounts()` (paginated)
- Transaction methods: `get_latest_transaction_date(account_id)`,
  `create_transaction(payload)`
- Reporting methods: `get_bills()`, `get_budgets()`,
  `get_budget_limits(budget_id)`, `get_categories()`, `get_summary()`

## Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv)

## Adding to a project (git subtree)

The recommended way to consume this library is as a git subtree. The library
lives inside the consuming project at `libs/firefly-python-api/` and is
referenced as a local path dependency — no PyPI publishing needed.

**Add (first time):**

```bash
git subtree add --prefix=libs/firefly-python-api \
  https://github.com/CmdrPrompt/firefly-python-api main --squash
```

**Reference in `pyproject.toml`:**

```toml
[project]
dependencies = [
    "firefly-python-api",
]

[tool.uv.sources]
firefly-python-api = { path = "libs/firefly-python-api" }
```

**Pull updates later:**

```bash
git subtree pull --prefix=libs/firefly-python-api \
  https://github.com/CmdrPrompt/firefly-python-api main --squash
```

## Usage

```python
from firefly_python_api import FireflyClient, load_config, FireflyConnectionError

url, token = load_config(".env")
client = FireflyClient(url, token)
client.validate_connection()

accounts = client.get_asset_accounts()
```

## Development

```bash
make install       # install dependencies and pre-commit hooks
make test          # run tests with coverage
make lint          # run ruff, mypy, bandit
make help          # list all available targets
```

## License

MIT
