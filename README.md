# firefly-bills-analyzer

Analyzes your Firefly III transaction history to automatically identify recurring payments and create subscriptions (bills) via the Firefly III API. Designed for cash flow planning across the full year, including low-frequency bills such as quarterly and annual payments.

> **Status:** Under development. Not yet functional.

## Features

- Detects recurring payments by grouping transactions per payee and analyzing frequency and amount patterns
- Estimates recurrence as monthly, quarterly, half-yearly, or yearly
- Assigns a confidence score to each suggestion based on pattern strength and category
- Web UI for reviewing, adjusting, and approving suggestions before anything is written to Firefly III
- Category-aware filtering: include or exclude transactions by Firefly III category, with optional confidence boost for known bill categories
- Dry-run mode for reviewing suggestions without creating any bills
- Export suggestions to CSV or JSON
- Local disk cache to minimize API calls to Firefly III
- CLI mode for scripted or automated use

## Requirements

- Firefly III v6+ with REST API enabled and a Personal Access Token
- Docker and Docker Compose

## Getting started

```bash
git clone https://github.com/CmdrPrompt/firefly-bills-analyzer.git 
cd firefly-bills-analyzer
cp .env.example .env
# Edit .env with your Firefly III URL and token
docker compose up -d
```

Then open `http://localhost:5000` in your browser.

## Configuration

All configuration is done via environment variables or a `.env` file. See `.env.example` for available options.

Key parameters:

| Variable | Description | Default |
|---|---|---|
| `FIREFLY_URL` | Base URL of your Firefly III instance | *(required)* |
| `FIREFLY_TOKEN` | Personal Access Token | *(required)* |
| `LOOKBACK_MONTHS` | Months of transaction history to analyze | `24` |
| `MIN_OCCURRENCES` | Minimum occurrences to classify as recurring | `2` |
| `HIGH_CONFIDENCE_THRESHOLD` | Confidence threshold for auto-approval in CLI mode | `0.80` |
| `WEB_PORT` | Port the web server listens on | `5000` |

See `.env.example` for the full list.

## CLI mode

```bash
docker compose run bills-analyzer python app.py --cli [--dry-run] [--auto-approve] [--clear-cache]
```

## TrueNAS Scale

The container runs without modifications on TrueNAS Scale. If Firefly III is running as a separate container on the same NAS, set `FIREFLY_URL` to the NAS host IP (e.g. `http://192.168.1.x:8080`) or configure a shared Docker network in `docker-compose.yml`.

## License

MIT
