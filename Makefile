.DEFAULT_GOAL := help
.PHONY: help install dev install-uv prek-install upgrade
.PHONY: lint fmt fmt-check fmt-fix ruff ruff-check type-check
.PHONY: security
.PHONY: test test-cov test-fast test-debug test-failed
.PHONY: docs docs-serve docs-clean changelog
.PHONY: build clean destroy
.PHONY: frontend frontend-dev frontend-lint frontend-build
.PHONY: wt worktree wt-ls worktree-list wt-j worktree-jump worktree-prune
.PHONY: ci ci-security ci-lint ci-test ci-frontend ci-install act act-ci act-list

# =============================================================================
# Variables
# =============================================================================

SRC_DIR := src
TEST_DIR := tests
DOCS_DIR := docs
FRONTEND_DIR := frontend
PKG_NAME := litestar_admin

# =============================================================================
# Help
# =============================================================================

help: ## Show this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z0-9_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

# =============================================================================
# Setup & Installation
# =============================================================================

##@ Setup & Installation

install-uv: ## Install latest version of uv
	@curl -LsSf https://astral.sh/uv/install.sh | sh

install: ## Install package (production mode)
	@uv sync --no-dev

dev: ## Install package with all development dependencies
	@uv sync --all-extras

prek-install: ## Install prek hooks
	@prek install
	@prek install --hook-type commit-msg
	@prek install --hook-type pre-push

upgrade: ## Upgrade all dependencies
	@uv lock --upgrade

# =============================================================================
# Code Quality
# =============================================================================

##@ Code Quality

lint: ## Run prek hooks (ruff, codespell, etc.)
	@prek run --all-files

fmt: ## Format code with ruff
	@uv run --no-sync ruff format $(SRC_DIR) $(TEST_DIR)

fmt-check: ## Check formatting without changes
	@uv run --no-sync ruff format --check $(SRC_DIR) $(TEST_DIR)

fmt-fix: ## Run ruff with auto-fix
	@uv run --no-sync ruff check --fix $(SRC_DIR) $(TEST_DIR)

ruff: ## Run ruff with unsafe fixes
	@uv run --no-sync ruff check . --unsafe-fixes --fix

ruff-check: ## Run ruff without changes
	@uv run --no-sync ruff check $(SRC_DIR) $(TEST_DIR)

type-check: ## Run ty type checker
	@uv run --no-sync ty check $(SRC_DIR)

# =============================================================================
# Security
# =============================================================================

##@ Security

security: ## Run zizmor GitHub Actions security scanner
	@uvx zizmor .github/workflows/

# =============================================================================
# Testing
# =============================================================================

##@ Testing

test: ## Run test suite
	@PYTHONDONTWRITEBYTECODE=1 uv run --no-sync pytest

test-cov: ## Run tests with coverage report
	@PYTHONDONTWRITEBYTECODE=1 uv run --no-sync pytest --cov=$(SRC_DIR)/$(PKG_NAME) --cov-report=term-missing --cov-report=html

test-fast: ## Run tests quickly (fail fast, quiet)
	@PYTHONDONTWRITEBYTECODE=1 uv run --no-sync pytest -x -q

test-debug: ## Run tests with verbose output
	@PYTHONDONTWRITEBYTECODE=1 uv run --no-sync pytest -vv -s

test-failed: ## Re-run only failed tests
	@PYTHONDONTWRITEBYTECODE=1 uv run --no-sync pytest --lf

# =============================================================================
# Documentation
# =============================================================================

##@ Documentation

docs: docs-clean ## Build documentation
	@uv sync --group docs
	@uv run sphinx-build -M html $(DOCS_DIR) $(DOCS_DIR)/_build -E -a -j auto

docs-serve: docs-clean ## Serve documentation with live reload
	@uv sync --group docs
	@uv run sphinx-autobuild $(DOCS_DIR) $(DOCS_DIR)/_build/html -j auto --open-browser --port 0

docs-clean: ## Clean built documentation
	@rm -rf $(DOCS_DIR)/_build

changelog: ## Generate changelog with git-cliff
	@uvx git-cliff -o $(DOCS_DIR)/changelog.md

# =============================================================================
# Frontend
# =============================================================================

##@ Frontend

frontend: ## Build frontend for production
	@cd $(FRONTEND_DIR) && bun install && bun run build
	@rm -rf $(SRC_DIR)/$(PKG_NAME)/static
	@cp -r $(FRONTEND_DIR)/out $(SRC_DIR)/$(PKG_NAME)/static

frontend-dev: ## Run frontend dev server
	@cd $(FRONTEND_DIR) && bun install && bun run dev

frontend-lint: ## Lint frontend with oxlint
	@cd $(FRONTEND_DIR) && bun run lint

frontend-build: ## Build frontend without copying
	@cd $(FRONTEND_DIR) && bun install && bun run build

# =============================================================================
# Build & Release
# =============================================================================

##@ Build & Release

build: clean ## Build package
	@uv build

clean: ## Clean build artifacts and caches
	@rm -rf .pytest_cache .ruff_cache .mypy_cache .hypothesis
	@rm -rf build/ dist/ .eggs/
	@find . -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
	@find . -name '*.egg' -exec rm -rf {} + 2>/dev/null || true
	@find . -name '*.pyc' -exec rm -rf {} + 2>/dev/null || true
	@find . -name '*.pyo' -exec rm -rf {} + 2>/dev/null || true
	@find . -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .coverage coverage.xml htmlcov/

destroy: clean docs-clean ## Remove virtual environment and all artifacts
	@rm -rf .venv
	@rm -rf $(FRONTEND_DIR)/node_modules $(FRONTEND_DIR)/.next $(FRONTEND_DIR)/out

# =============================================================================
# Git Worktrees
# =============================================================================

##@ Git Worktrees

wt: worktree ## Alias for worktree
worktree: ## Create a new git worktree (Usage: make wt NAME=my-feature)
	@if [ -z "$(NAME)" ]; then \
		echo "Error: NAME required. Usage: make wt NAME=feature-name"; \
		exit 1; \
	fi
	@mkdir -p .worktrees
	@git checkout main && git pull
	@git worktree add -b $(NAME) .worktrees/$(NAME) main
	@echo "Created worktree at .worktrees/$(NAME)"

wt-ls: worktree-list ## Alias for worktree-list
worktree-list: ## List all git worktrees
	@git worktree list

wt-j: worktree-jump ## Alias for worktree-jump
worktree-jump: ## Jump to a worktree (Usage: cd $$(make wt-j NAME=foo))
	@if [ -z "$(NAME)" ]; then \
		echo "Available worktrees:"; \
		git worktree list --porcelain | grep "^worktree" | cut -d' ' -f2; \
		echo ""; \
		echo "Usage: cd \$$(make wt-j NAME=<name>)"; \
	else \
		path=".worktrees/$(NAME)"; \
		if [ -d "$$path" ]; then \
			echo "$$path"; \
		else \
			echo "Worktree not found: $$path" >&2; \
			exit 1; \
		fi; \
	fi

worktree-prune: ## Clean up stale git worktrees
	@git worktree prune -v

# =============================================================================
# CI Helpers
# =============================================================================

##@ CI Helpers

ci: ci-security ci-lint ci-test ci-frontend ## Run all CI checks locally
	@echo "\n\033[32m✓ All CI checks passed!\033[0m"

ci-security: ## Run security scan (zizmor)
	@echo "\033[36m→ Running workflow security scan...\033[0m"
	@uvx zizmor .github/workflows/

ci-lint: ## Run lint, format check, and type check
	@echo "\033[36m→ Running ruff check...\033[0m"
	@uv run --no-sync ruff check $(SRC_DIR) $(TEST_DIR)
	@echo "\033[36m→ Running ruff format check...\033[0m"
	@uv run --no-sync ruff format --check $(SRC_DIR) $(TEST_DIR)
	@echo "\033[36m→ Running ty type checker...\033[0m"
	@uv run --no-sync ty check $(SRC_DIR)

ci-test: ## Run test suite
	@echo "\033[36m→ Running tests...\033[0m"
	@PYTHONDONTWRITEBYTECODE=1 uv run --no-sync pytest

ci-frontend: ## Run frontend lint
	@echo "\033[36m→ Running frontend lint (oxlint)...\033[0m"
	@cd $(FRONTEND_DIR) && bun run lint

ci-install: ## Install for CI (frozen dependencies)
	@uv sync --all-extras --frozen

act: act-list ## List available act jobs
act-list: ## List available GitHub Actions jobs
	@act -l

act-ci: ## Run CI workflow locally with act
	@act push -W .github/workflows/ci.yml --container-architecture linux/amd64
