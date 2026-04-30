include .butler/Makefile

test:
	uv run pytest tests/ --ignore=tests/integration --cov=src --cov-report=term-missing

test-integration:
	uv run pytest tests/integration/ -v
