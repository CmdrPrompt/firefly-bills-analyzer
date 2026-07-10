.PHONY: all help setup install lint check-agents-sync validate-agents check-butler fix stage branch-task sync-main stage-task commit-task \
        commit-output pr-task merge-pr stage-current-task commit-current-task pr-current-task \
	merge-current-task merge-worktree test clean clean-complexity generate-governance-files \
	generate-pyproject generate-gitignore generate-pre-commit-config generate-pymarkdown init-project \
	butler-trim butler-fetch butler-pull butler-check butler-uninstall

BUTLER_REMOTE ?= https://github.com/CmdrPrompt/python-butler.git
TASKS_DIR ?= docs/tasks
SRC_DIR ?= src
TESTS_DIR ?= tests
PROJECT_NAME ?= my-project
PROJECT_DESCRIPTION ?= Describe your project here.
REQUIREMENTS_PATH ?= docs/REQUIREMENTS.md
WORKFLOW_GUARDIAN_NAME ?= Workflow Guardian
WORKFLOW_GUARDIAN_REF ?= Workflow Guardian agent (`.github/agents/workflow-guardian.agent.md`)
BUG_TRIAGE_NAME ?= Bug Triage
PROJECT_MAKE_TARGET ?= make help
GUIDELINES_TITLE ?= Python Development Guidelines

all: help

## Show this help text
help:
	@echo ""
	@echo "Available commands:"
	@echo ""
	@echo "  Keeping butler up to date:"
	@echo "    make butler-check  -- Check if butler updates are available"
	@echo "    make butler-pull   -- Pull butler updates and trim (updates .butler/Makefile only)"
	@echo "    make butler-fetch  -- Pull butler without trimming (use before regenerating files)"
	@echo "    make butler-trim   -- Remove all but .butler/Makefile (run after init-project)"
	@echo ""
	@echo "  Removing butler:"
	@echo "    make butler-uninstall CATEGORIES=subtree,makefile,governance  -- Remove butler's footprint (add DRY_RUN=1 or FORCE=1)"
	@echo ""
	@echo "  First time on a new project:"
	@echo "    make init-project  -- Interactively generate CLAUDE.md and governance files"
	@echo ""
	@echo "  First time on a new machine:"
	@echo "    make setup    -- Install uv (if missing)"
	@echo "    make install  -- Create venv, install dependencies and activate pre-commit"
	@echo ""
	@echo "  Daily use:"
	@echo "    make lint     -- Run ruff, mypy, bandit, pymarkdown and complexipy"
	@echo "    make fix      -- Auto-fix ruff and pymarkdown issues"
	@echo "    make stage    -- Auto-fix and re-stage all staged changes"
	@echo "    make test     -- Run pytest with coverage"
	@echo "    make validate-agents  -- Validate agent definitions (frontmatter and tool names)"
	@echo ""
	@echo "  Governance templates:"
	@echo "    make generate-governance-files  -- Generate CLAUDE.md, .github/copilot-instructions.md, and .github/chatmodes/"
	@echo ""
	@echo "  Task workflow (explicit task ID):"
	@echo "    make branch-task f=TASK-001  -- Create/switch to task branch"
	@echo "    make sync-main               -- Merge main into current task branch"
	@echo "    make stage-task f=TASK-001   -- Fix + stage files listed in task"
	@echo "    make commit-task f=TASK-001  -- Commit with message from task file"
	@echo "    make pr-task f=TASK-001      -- Open PR on GitHub"
	@echo "    make merge-pr f=TASK-001     -- Squash-merge PR, pull main"
	@echo ""
	@echo "  Task workflow (current branch):"
	@echo "    make stage-current-task      -- Fix + stage files for current task"
	@echo "    make commit-current-task     -- Commit for current task"
	@echo "    make pr-current-task         -- Open PR for current task"
	@echo "    make merge-current-task      -- Squash-merge PR, pull main"
	@echo ""
	@echo "  Agent / worktree helpers:"
	@echo "    make sync-main                          -- Merge main into current branch"
	@echo "    make merge-worktree b=<branch>          -- Squash-merge a worktree branch into current branch"
	@echo "    make commit-output f='files' m='msg'    -- Stage and commit arbitrary files"
	@echo ""

## Generate pyproject.toml and .pymarkdown from templates if missing
generate-pyproject:
	@[ ! -f pyproject.toml ] || [ "$(FORCE)" = "1" ] || \
		(echo "pyproject.toml already exists. Run with FORCE=1 to overwrite."; exit 1)
	@sed \
		-e 's|{{PROJECT_NAME}}|$(PROJECT_NAME)|g' \
		-e 's|{{PROJECT_DESCRIPTION}}|$(PROJECT_DESCRIPTION)|g' \
		-e 's|{{TESTS_DIR}}|$(TESTS_DIR)|g' \
		-e 's|{{SRC_DIR}}|$(SRC_DIR)|g' \
		.butler/scaffold/pyproject.toml.tmpl > pyproject.toml
	@echo "✓ Generated pyproject.toml"
	@$(MAKE) generate-pymarkdown FORCE=$(FORCE)

## Generate .pymarkdown config from scaffold
generate-pymarkdown:
	@[ ! -f .pymarkdown ] || [ "$(FORCE)" = "1" ] || \
		(echo ".pymarkdown already exists. Run with FORCE=1 to overwrite."; exit 1)
	@cp .butler/scaffold/.pymarkdown .pymarkdown
	@echo "✓ Generated .pymarkdown"

## Generate .gitignore from scaffold template
generate-gitignore:
	@[ ! -f .gitignore ] || [ "$(FORCE)" = "1" ] || \
		(echo ".gitignore already exists. Run with FORCE=1 to overwrite."; exit 1)
	@cp .butler/scaffold/.gitignore.tmpl .gitignore
	@echo "✓ Generated .gitignore"

## Generate .pre-commit-config.yaml from scaffold template
generate-pre-commit-config:
	@[ ! -f .pre-commit-config.yaml ] || [ "$(FORCE)" = "1" ] || \
		(echo ".pre-commit-config.yaml already exists. Run with FORCE=1 to overwrite."; exit 1)
	@cp .butler/scaffold/.pre-commit-config.yaml.tmpl .pre-commit-config.yaml
	@echo "✓ Generated .pre-commit-config.yaml"

## Install uv if missing (run once per machine)
setup:
	@which uv > /dev/null 2>&1 && echo "✓ uv already installed" || \
		(curl -LsSf https://astral.sh/uv/install.sh | sh && echo "✓ uv installed")

## Create virtual environment and install dependencies
install:
	@[ -f pyproject.toml ] || $(MAKE) generate-pyproject
	@[ -f .gitignore ] || $(MAKE) generate-gitignore
	@[ -f .pre-commit-config.yaml ] || $(MAKE) generate-pre-commit-config
	@[ -f .pymarkdown ] || $(MAKE) generate-pymarkdown
	uv sync --extra dev
	uv run pre-commit install
	@[ -f CLAUDE.md ] || $(MAKE) generate-governance-files
	@echo "✓ Environment ready"

## Fail if claude-agents/ and .claude/agents/ have drifted apart
check-agents-sync:
	@status=0; \
	for f in claude-agents/*.agent.md; do \
		base=$$(basename "$$f"); \
		other=".claude/agents/$$base"; \
		if [ ! -f "$$other" ]; then \
			echo "check-agents-sync: '$$base' exists in claude-agents/ but not in .claude/agents/"; \
			status=1; \
		elif ! diff -q "$$f" "$$other" > /dev/null 2>&1; then \
			echo "check-agents-sync: '$$base' differs between claude-agents/ and .claude/agents/"; \
			status=1; \
		fi; \
	done; \
	for f in .claude/agents/*.agent.md; do \
		base=$$(basename "$$f"); \
		[ -f "claude-agents/$$base" ] || { \
			echo "check-agents-sync: '$$base' exists in .claude/agents/ but not in claude-agents/"; \
			status=1; \
		}; \
	done; \
	if [ "$$status" -ne 0 ]; then \
		echo "claude-agents/ and .claude/agents/ must stay identical — sync the files above."; \
		exit 1; \
	fi

## Run linters
lint: check-agents-sync
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy $(SRC_DIR)/
	uv run bandit -r $(SRC_DIR)/ -c pyproject.toml
	uv run pymarkdown --config .pymarkdown scan \
		$(shell find . -name "*.md" -not -path "./.venv/*" -not -path "./.github/*" -not -path "./.butler/.github/*" -not -path "./libs/*" -not -path "./.claude/*")
	uv run complexipy $(SRC_DIR)/ -mx 15 -s desc -j || \
		([ -f scripts/explain_complexipy_failures.py ] && \
			uv run python scripts/explain_complexipy_failures.py --max 15; exit 1)

## Auto-fix ruff and pymarkdown issues
fix:
	uv run ruff check --fix .
	uv run ruff format .
	uv run pymarkdown --config .pymarkdown fix \
		$(shell find . -name "*.md" -not -path "./.venv/*" -not -path "./.github/*" -not -path "./.butler/.github/*" -not -path "./libs/*" -not -path "./.claude/*")

## Auto-fix and re-stage already-staged files (run before git commit)
stage:
	@STAGED=$$(git diff --name-only --cached); \
	uv run ruff check --fix .; \
	uv run ruff format .; \
	uv run pymarkdown --config .pymarkdown fix \
		$$(find . -name "*.md" -not -path "./.venv/*" -not -path "./.butler/.github/*" -not -path "./libs/*" -not -path "./.claude/*"); \
	[ -n "$$STAGED" ] && echo "$$STAGED" | xargs git add -- || true; \
	git update-index -q --refresh

## Fail with a clear message if butler-cli is not installed
check-butler:
	@command -v butler > /dev/null 2>&1 || \
		(echo "butler-cli is not installed. Install it with: uv pip install -e . (see README for details)"; exit 1)

## Create/switch task branch from task file: make branch-task f=TASK-001
branch-task: check-butler
	@[ -n "$(f)" ] || (echo "Usage: make branch-task f=<task-id>"; exit 1)
	butler --tasks-dir $(TASKS_DIR) task branch $(f)

## Merge main into the current task branch (sync before coding)
sync-main:
	@BRANCH=$$(git branch --show-current); \
	[ "$$BRANCH" != "main" ] || (echo "Already on main — switch to a task branch first"; exit 1)
	git merge main

## Auto-fix and stage files listed in a task file: make stage-task f=TASK-001
stage-task: check-butler
	@[ -n "$(f)" ] || (echo "Usage: make stage-task f=<task-id>"; exit 1)
	butler --tasks-dir $(TASKS_DIR) task stage $(f)

## Commit using message from task file: make commit-task f=TASK-001
commit-task: check-butler
	@[ -n "$(f)" ] || (echo "Usage: make commit-task f=<task-id>"; exit 1)
	butler --tasks-dir $(TASKS_DIR) task commit $(f)

## Auto-fix and stage files for the current task branch
stage-current-task:
	@BRANCH=$$(git branch --show-current); \
	NUM=$$(echo "$$BRANCH" | sed -n 's#^task/\([0-9][0-9][0-9]\)-.*#\1#p'); \
	[ -n "$$NUM" ] || (echo "Not on a task branch (expected task/<NNN>-...)"; exit 1); \
	$(MAKE) stage-task f=TASK-$$NUM

## Commit using task file metadata for the current task branch
commit-current-task:
	@BRANCH=$$(git branch --show-current); \
	NUM=$$(echo "$$BRANCH" | sed -n 's#^task/\([0-9][0-9][0-9]\)-.*#\1#p'); \
	[ -n "$$NUM" ] || (echo "Not on a task branch (expected task/<NNN>-...)"; exit 1); \
	$(MAKE) commit-task f=TASK-$$NUM

## Stage and commit arbitrary files with a given message (for agents not on a task branch)
commit-output:
	@[ -n "$(f)" ] || (echo "Usage: make commit-output f='file1 file2' m='commit message'"; exit 1)
	@[ -n "$(m)" ] || (echo "Usage: make commit-output f='file1 file2' m='commit message'"; exit 1)
	git add -- $(f)
	git commit -m "$(m)"

## Open a GitHub PR using task title and description: make pr-task f=TASK-001
pr-task: check-butler
	@[ -n "$(f)" ] || (echo "Usage: make pr-task f=<task-id>"; exit 1)
	butler --tasks-dir $(TASKS_DIR) task branch $(f)
	butler --tasks-dir $(TASKS_DIR) task pr $(f)

## Open PR using task file metadata for the current task branch
pr-current-task:
	@BRANCH=$$(git branch --show-current); \
	NUM=$$(echo "$$BRANCH" | sed -n 's#^task/\([0-9][0-9][0-9]\)-.*#\1#p'); \
	[ -n "$$NUM" ] || (echo "Not on a task branch (expected task/<NNN>-...)"; exit 1); \
	$(MAKE) pr-task f=TASK-$$NUM

## Squash-merge the open PR for a task branch: make merge-pr f=TASK-001
merge-pr: check-butler
	@[ -n "$(f)" ] || (echo "Usage: make merge-pr f=<task-id>"; exit 1)
	butler --tasks-dir $(TASKS_DIR) task merge $(f)

## Squash-merge the open PR for the current task branch, then pull main
merge-current-task:
	@BRANCH=$$(git branch --show-current); \
	NUM=$$(echo "$$BRANCH" | sed -n 's#^task/\([0-9][0-9][0-9]\)-.*#\1#p'); \
	[ -n "$$NUM" ] || (echo "Not on a task branch (expected task/<NNN>-...)"; exit 1); \
	$(MAKE) merge-pr f=TASK-$$NUM

## Squash a worktree sub-agent branch's commit(s) into staged changes on the current branch
merge-worktree:
	@[ -n "$(b)" ] || (echo "Usage: make merge-worktree b=<branch-name>"; exit 1)
	git merge --squash $(b)

## Run tests with coverage
test:
	uv run pytest $(TESTS_DIR)/ --cov=$(SRC_DIR) --cov-report=term-missing

## Interactively prompt for project values and generate governance files
init-project:
	@echo "Initialising project governance files."
	@echo "Press Enter to accept the default shown in brackets."
	@echo ""
	@read -p "Project name [$(notdir $(CURDIR))]: " pname; \
	pname=$${pname:-$(notdir $(CURDIR))}; \
	read -p "Project description [$(PROJECT_DESCRIPTION)]: " pdesc; \
	pdesc=$${pdesc:-$(PROJECT_DESCRIPTION)}; \
	read -p "Requirements path [$(REQUIREMENTS_PATH)]: " rpath; \
	rpath=$${rpath:-$(REQUIREMENTS_PATH)}; \
	read -p "Run command [$(PROJECT_MAKE_TARGET)]: " ptarget; \
	ptarget=$${ptarget:-$(PROJECT_MAKE_TARGET)}; \
	echo ""; \
	$(MAKE) generate-governance-files FORCE=$(FORCE) \
		PROJECT_NAME="$$pname" \
		PROJECT_DESCRIPTION="$$pdesc" \
		REQUIREMENTS_PATH="$$rpath" \
		PROJECT_MAKE_TARGET="$$ptarget"; \
	$(MAKE) generate-pyproject FORCE=$(FORCE) \
		PROJECT_NAME="$$pname" \
		PROJECT_DESCRIPTION="$$pdesc"; \
	$(MAKE) generate-gitignore FORCE=$(FORCE); \
	$(MAKE) generate-pre-commit-config FORCE=$(FORCE); \
	echo ""; \
	echo "✓ Done. Stage and commit with:"; \
	echo ""; \
	echo "  git add CLAUDE.md pyproject.toml .gitignore .pre-commit-config.yaml .github/ .claude/"; \
	echo "  git commit -m \"Bootstrap project with python-butler\""

## Remove all but .butler/Makefile — run after make init-project (idempotent)
butler-trim:
	@echo "Trimming .butler/ down to Makefile only ..."
	@FILES=$$(git ls-files .butler/ | grep -v '^\.butler/Makefile$$'); \
	[ -n "$$FILES" ] && echo "$$FILES" | xargs git rm -r --cached --ignore-unmatch || true
	@find .butler/ -mindepth 1 -maxdepth 1 ! -name 'Makefile' -exec rm -rf {} +
	@BUTLER_SHA=$$(git ls-remote $(BUTLER_REMOTE) refs/heads/main | cut -f1); \
	if [ -n "$$BUTLER_SHA" ]; then \
		echo "$$BUTLER_SHA" > .butler-version; \
		echo "✓ Recorded butler version: $$BUTLER_SHA"; \
	else \
		echo "Warning: could not reach $(BUTLER_REMOTE) — .butler-version not written"; \
	fi
	@echo "✓ Trim complete. Stage and commit with:"
	@echo ""
	@echo "  git add -A .butler/ .butler-version"
	@echo "  git commit -m \"chore: trim .butler/ down to Makefile\""

## Remove butler's footprint from this project. Never touches docs/tasks/.
## Usage: make butler-uninstall CATEGORIES=subtree,makefile,governance [DRY_RUN=1] [FORCE=1]
## Pure shell (grep/sed/rm) so it works even without butler_core/butler-cli installed
## (e.g. a legacy project that adopted butler before the CLI existed).
butler-uninstall:
	@[ -n "$(CATEGORIES)" ] || (echo "Usage: make butler-uninstall CATEGORIES=subtree,makefile,governance [DRY_RUN=1] [FORCE=1]"; exit 1)
	@if [ -z "$(FORCE)" ] && [ -n "$$(git status --porcelain)" ]; then \
		echo "Error: working tree has uncommitted changes. Commit/stash first, or pass FORCE=1."; \
		exit 1; \
	fi
	@WANT_SUBTREE=$$(echo "$(CATEGORIES)" | tr ',' '\n' | grep -qx subtree && echo 1 || echo ""); \
	WANT_MAKEFILE=$$(echo "$(CATEGORIES)" | tr ',' '\n' | grep -qx makefile && echo 1 || echo ""); \
	WANT_GOVERNANCE=$$(echo "$(CATEGORIES)" | tr ',' '\n' | grep -qx governance && echo 1 || echo ""); \
	if [ -n "$$WANT_SUBTREE" ] && [ -d .butler ]; then \
		if [ -n "$(DRY_RUN)" ]; then echo "Would remove .butler/"; \
		else rm -rf .butler; echo "Removed .butler/"; fi; \
	fi; \
	if [ -n "$$WANT_MAKEFILE" ] && [ -f Makefile ] && grep -q '^include \.butler/Makefile$$' Makefile; then \
		if [ -n "$(DRY_RUN)" ]; then echo "Would remove 'include .butler/Makefile' line from Makefile"; \
		else \
			grep -v '^include \.butler/Makefile$$' Makefile > Makefile.tmp && mv Makefile.tmp Makefile; \
			echo "Removed 'include .butler/Makefile' line from Makefile"; \
		fi; \
	fi; \
	if [ -n "$$WANT_GOVERNANCE" ]; then \
		for p in CLAUDE.md .github/copilot-instructions.md .github/agents .claude/agents; do \
			if [ -e "$$p" ]; then \
				if [ -n "$(DRY_RUN)" ]; then echo "Would remove $$p"; \
				else rm -rf "$$p"; echo "Removed $$p"; fi; \
			fi; \
		done; \
	fi
	@echo ""
	@echo "docs/tasks/ was not touched."

## Check if butler updates are available
butler-check:
	@CURRENT=$$(cat .butler-version 2>/dev/null); \
	echo "Checking for butler updates..."; \
	LATEST=$$(git ls-remote $(BUTLER_REMOTE) refs/heads/main | cut -f1); \
	[ -n "$$LATEST" ] || (echo "Could not reach $(BUTLER_REMOTE)"; exit 1); \
	if [ -z "$$CURRENT" ]; then \
		echo "No .butler-version found — assuming updates are available."; \
		echo "  Latest: $$LATEST"; \
		echo "  Run: make butler-pull"; \
	elif [ "$$CURRENT" = "$$LATEST" ]; then \
		echo "✓ butler is up to date ($$CURRENT)"; \
	else \
		echo "Updates available."; \
		echo "  Current: $$CURRENT"; \
		echo "  Latest:  $$LATEST"; \
		echo "  Run: make butler-pull"; \
	fi

## Pull the latest butler without trimming — use before regenerating governance files
butler-fetch:
	git subtree pull --prefix=.butler $(BUTLER_REMOTE) main --squash

## Pull the latest butler and trim — updates .butler/Makefile only
butler-pull:
	git subtree pull --prefix=.butler $(BUTLER_REMOTE) main --squash
	$(MAKE) butler-trim

## Generate project governance files from .butler templates
generate-governance-files:
	@[ ! -f CLAUDE.md ] || [ "$(FORCE)" = "1" ] || \
		(echo "CLAUDE.md already exists. Run with FORCE=1 to overwrite."; exit 1)
	@[ ! -f .github/copilot-instructions.md ] || [ "$(FORCE)" = "1" ] || \
		(echo ".github/copilot-instructions.md already exists. Run with FORCE=1 to overwrite."; exit 1)
	@mkdir -p .github .github/agents
	@sed \
		-e 's|{{PROJECT_NAME}}|$(PROJECT_NAME)|g' \
		-e 's|{{PROJECT_DESCRIPTION}}|$(PROJECT_DESCRIPTION)|g' \
		-e 's|{{REQUIREMENTS_PATH}}|$(REQUIREMENTS_PATH)|g' \
		-e 's|{{WORKFLOW_GUARDIAN_NAME}}|$(WORKFLOW_GUARDIAN_NAME)|g' \
		-e 's|{{BUG_TRIAGE_NAME}}|$(BUG_TRIAGE_NAME)|g' \
		-e 's|{{PROJECT_MAKE_TARGET}}|$(PROJECT_MAKE_TARGET)|g' \
		.butler/templates/CLAUDE.md.tmpl > CLAUDE.md
	@sed \
		-e 's|{{GUIDELINES_TITLE}}|$(GUIDELINES_TITLE)|g' \
		-e 's|{{PROJECT_DESCRIPTION}}|$(PROJECT_DESCRIPTION)|g' \
		-e 's|{{REQUIREMENTS_PATH}}|$(REQUIREMENTS_PATH)|g' \
		-e 's|{{WORKFLOW_GUARDIAN_REF}}|$(WORKFLOW_GUARDIAN_REF)|g' \
		-e 's|{{BUG_TRIAGE_NAME}}|$(BUG_TRIAGE_NAME)|g' \
		.butler/templates/copilot-instructions.md.tmpl > .github/copilot-instructions.md
	@for agent in workflow-guardian implementation-worker bug-triage characterization-test-writer requirements-drafter task-drafter pr-reviewer dependency-auditor test-design-reviewer test-writer; do \
		sed \
			-e 's|{{REQUIREMENTS_PATH}}|$(REQUIREMENTS_PATH)|g' \
			.butler/templates/$$agent.agent.md.tmpl > .github/agents/$$agent.agent.md; \
	done
	@mkdir -p .claude/agents
	@cp .butler/claude-agents/*.agent.md .claude/agents/
	@echo "✓ Generated CLAUDE.md, .github/copilot-instructions.md, .github/agents/, and .claude/agents/"

## Remove generated complexipy artifacts
clean-complexity:
	rm -rf .complexipy_cache
	rm -f complexipy_results_*.json
	@echo "✓ Removed complexipy artifacts"

## Remove venv and cache
clean:
	$(MAKE) clean-complexity
	rm -rf .venv
	find . -type d \( -name "__pycache__" -o -name ".mypy_cache" \
		-o -name ".ruff_cache" -o -name ".pytest_cache" -o -name "*.egg-info" \) \
		-exec rm -rf {} +
	@echo "✓ Done"

## Validate agent logs
validate-agents:
	@python3 scripts/validate_agents.py .claude/agents