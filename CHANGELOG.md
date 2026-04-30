# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- `FireflyClient(url, token)` wraps `requests.Session` with `Authorization: Bearer`, `Accept: application/json`, and `Content-Type: application/json` headers (TASK-001)
- `FireflyClient.validate_connection()` verifies server reachability via `GET /api/v1/about`; raises `FireflyConnectionError` on network or HTTP failure (TASK-001)
- `load_config(env_path)` reads `FIREFLY_URL` and `FIREFLY_TOKEN` from the environment or a `.env` file; raises `ValueError` when either value is absent (TASK-001)
