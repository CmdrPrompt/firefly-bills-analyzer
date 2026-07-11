include .butler/Makefile

.PHONY: benchmark benchmark-real

## Run the analyzer performance benchmark (NFR-05); not part of `make test`
benchmark:
	uv run python tests/benchmark_analyzer.py

## Run the analyzer against real Firefly III data (read-only, requires .env); not part of `make test` or `make benchmark`
benchmark-real:
	uv run python scripts/benchmark_real_data.py
