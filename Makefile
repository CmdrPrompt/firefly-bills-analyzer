include .butler/Makefile

.PHONY: help
help:
	@$(MAKE) --no-print-directory -f .butler/Makefile help
	@echo "  Project tests:"
	@echo "    make test              -- Run unit tests with coverage (excludes integration)"
	@echo "    make test-integration  -- Run integration tests against a live Firefly III instance"
	@echo ""

test:
	uv run pytest tests/ --ignore=tests/integration --cov=src --cov-report=term-missing

test-integration:
	uv run pytest tests/integration/ -v
