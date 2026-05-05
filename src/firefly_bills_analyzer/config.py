"""Load all runtime configuration from environment variables / .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


class ConfigError(ValueError):
    """Raised when a required configuration value is absent or invalid."""


@dataclass(frozen=True)
class Config:
    # Required
    firefly_url: str
    firefly_token: str
    # Analysis
    lookback_months: int
    min_occurrences: int
    amount_margin: float
    high_confidence_threshold: float
    category_confidence_boost: float
    uncategorized_behavior: str
    include_categories: list[str]
    exclude_categories: list[str]
    # Output
    dry_run: bool
    export_format: str
    # Server
    web_port: int
    web_host: str
    # Cache
    cache_dir: str
    cache_ttl_categories: int
    cache_ttl_bills: int
    cache_ttl_transactions: int
    cache_ttl_payees: int

    @classmethod
    def from_env(cls) -> Config:
        url = os.environ.get("FIREFLY_URL", "").strip()
        if not url:
            raise ConfigError("FIREFLY_URL is required but not set.")

        token = os.environ.get("FIREFLY_TOKEN", "").strip()
        if not token:
            raise ConfigError("FIREFLY_TOKEN is required but not set.")

        def _csv(key: str) -> list[str]:
            raw = os.environ.get(key, "").strip()
            return [x.strip() for x in raw.split(",") if x.strip()] if raw else []

        return cls(
            firefly_url=url,
            firefly_token=token,
            lookback_months=int(os.environ.get("LOOKBACK_MONTHS", "24")),
            min_occurrences=int(os.environ.get("MIN_OCCURRENCES", "2")),
            amount_margin=float(os.environ.get("AMOUNT_MARGIN", "0.10")),
            high_confidence_threshold=float(os.environ.get("HIGH_CONFIDENCE_THRESHOLD", "0.80")),
            category_confidence_boost=float(os.environ.get("CATEGORY_CONFIDENCE_BOOST", "0.15")),
            uncategorized_behavior=os.environ.get("UNCATEGORIZED_BEHAVIOR", "neutral"),
            include_categories=_csv("INCLUDE_CATEGORIES"),
            exclude_categories=_csv("EXCLUDE_CATEGORIES"),
            dry_run=os.environ.get("DRY_RUN", "false").lower() in ("1", "true", "yes"),
            export_format=os.environ.get("EXPORT_FORMAT", "none"),
            web_port=int(os.environ.get("WEB_PORT", "5000")),
            web_host=os.environ.get("WEB_HOST", "127.0.0.1"),
            cache_dir=os.environ.get("CACHE_DIR", "./cache"),
            cache_ttl_categories=int(os.environ.get("CACHE_TTL_CATEGORIES", "86400")),
            cache_ttl_bills=int(os.environ.get("CACHE_TTL_BILLS", "3600")),
            cache_ttl_transactions=int(os.environ.get("CACHE_TTL_TRANSACTIONS", "3600")),
            cache_ttl_payees=int(os.environ.get("CACHE_TTL_PAYEES", "86400")),
        )
