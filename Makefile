include .butler/Makefile

.PHONY: benchmark

## Run the analyzer performance benchmark (NFR-05); not part of `make test`
benchmark:
	uv run python tests/benchmark_analyzer.py
