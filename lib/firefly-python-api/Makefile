include .butler/Makefile

.PHONY: help
help:
	@$(MAKE) --no-print-directory -f .butler/Makefile help
	@echo "  Project tests:"
	@echo "    make test              -- Run unit tests with coverage (excludes integration)"
	@echo "    make test-integration  -- Run integration tests against a live Firefly III instance"
	@echo ""

test:
	uv run pytest $(TESTS_DIR)/ --ignore=tests/integration --cov=$(SRC_DIR) --cov-report=term-missing

test-integration:
	uv run pytest tests/integration/ -v  --cov=$(SRC_DIR) --cov-report=term-missing
