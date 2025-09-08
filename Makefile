# Pipeline & Peril - Makefile
# Uses GNU Make (gmake) features
#
# Make History:
# - make: Created by Stuart Feldman at Bell Labs (1976)
# - GNU Make: Written by Richard Stallman and Roland McGrath (1988)
# - Currently maintained by Paul D. Smith
#
# This Makefile follows best practices from the original creators:
# - Sentinels for directory creation and state tracking
# - Atomic file operations for reliability
# - Clear distinction between phony and file targets
# - Automatic variables ($@, $<, $^) used consistently

# Default shell for better error handling
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

# Make variables
MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules

# Project directories
BUILD_DIR := build
DIST_DIR := dist
DOCS_DIR := docs

# Sentinel files for directory creation
BUILD_SENTINEL := $(BUILD_DIR)/.sentinel
VENV_SENTINEL := .venv/.sentinel

# Python environment
PYTHON := python3
UV := uv
PYTEST := $(UV) run pytest
BLACK := $(UV) run black
RUFF := $(UV) run ruff

# === PHONY TARGETS ===
# These don't create files with the target name
.PHONY: help setup dev test lint format clean clean-all check

# Default target - show help
help:
	@echo "Pipeline & Peril - Development Tasks"
	@echo ""
	@echo "File Targets (create actual files):"
	@echo "  README.md         - Generate from README.org"
	@echo "  $(VENV_SENTINEL)  - Create Python virtual environment"
	@echo "  $(BUILD_SENTINEL) - Create build directory"
	@echo ""
	@echo "Phony Targets (perform actions):"
	@echo "  setup      - Complete project setup"
	@echo "  dev        - Install development dependencies"
	@echo "  test       - Run test suite"
	@echo "  lint       - Run linters (ruff)"
	@echo "  format     - Format code (black)"
	@echo "  check      - Run all checks (lint + test)"
	@echo "  clean      - Remove generated files"
	@echo "  clean-all  - Remove all generated files and environments"

# === NON-PHONY FILE TARGETS ===
# These create actual files and use timestamps for dependency tracking

# Sentinel for build directory creation
$(BUILD_SENTINEL):
	@echo "Creating build directory..."
	@mkdir -p $(BUILD_DIR)
	@touch $@

# Sentinel for Python virtual environment
$(VENV_SENTINEL): pyproject.toml
	@echo "Creating Python virtual environment with uv..."
	@$(UV) venv
	@$(UV) pip install -e .
	@mkdir -p $(dir $@)
	@touch $@
	@echo "✓ Python environment ready"

# Generate README.md from README.org (atomic write)
README.md: README.org
	@echo "Generating README.md from README.org..."
	@if command -v emacs >/dev/null 2>&1; then \
		emacs --batch \
			--eval "(require 'org)" \
			--eval "(setq org-export-with-toc t)" \
			--eval "(setq org-export-with-author t)" \
			--eval "(setq org-export-with-email nil)" \
			--eval "(find-file \"$<\")" \
			--eval "(org-md-export-to-markdown)" \
			--kill && \
		echo "✓ README.md generated successfully"; \
	else \
		echo "⚠ Emacs not found - creating placeholder README.md"; \
		echo "# Pipeline & Peril" > $@.tmp; \
		echo "" >> $@.tmp; \
		echo "This is a placeholder. Install Emacs to generate from README.org" >> $@.tmp; \
		mv $@.tmp $@; \
	fi

# Development dependencies installation marker
.dev-deps.stamp: $(VENV_SENTINEL) pyproject.toml
	@echo "Installing development dependencies..."
	@$(UV) pip install -e ".[dev]"
	@touch $@
	@echo "✓ Development dependencies installed"

# === PHONY TARGETS THAT DEPEND ON FILE TARGETS ===

# Complete setup
setup: $(VENV_SENTINEL) README.md $(BUILD_SENTINEL)
	@echo "✓ Setup complete!"

# Development environment
dev: .dev-deps.stamp
	@echo "✓ Development environment ready"

# Run tests (depends on dev environment)
test: .dev-deps.stamp
	@echo "Running tests..."
	@$(PYTEST) tests/ -v

# Run linter
lint: .dev-deps.stamp
	@echo "Running ruff..."
	@$(RUFF) check src/ tests/

# Format code
format: .dev-deps.stamp
	@echo "Formatting code with black..."
	@$(BLACK) src/ tests/

# Run all checks
check: lint test
	@echo "✓ All checks passed"

# === CLEAN TARGETS ===

# Clean generated files but preserve environment
clean:
	@echo "Cleaning generated files..."
	@rm -f README.md
	@rm -f .dev-deps.stamp
	@rm -rf $(BUILD_DIR)
	@rm -rf $(DIST_DIR)
	@rm -rf __pycache__
	@rm -rf .pytest_cache
	@rm -rf .coverage
	@rm -rf htmlcov
	@rm -rf *.egg-info
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*~" -delete
	@find . -type f -name "*.tmp" -delete
	@echo "✓ Clean complete"

# Clean everything including virtual environment
clean-all: clean
	@echo "Removing Python environment..."
	@rm -rf .venv
	@rm -f uv.lock
	@echo "✓ Full clean complete"

# === SPECIAL TARGETS ===

# Ensure directories exist for any rules that need them
$(BUILD_DIR) $(DIST_DIR):
	@mkdir -p $@

# Debug target to show variables
.PHONY: debug
debug:
	@echo "BUILD_DIR: $(BUILD_DIR)"
	@echo "VENV_SENTINEL: $(VENV_SENTINEL)"
	@echo "Shell: $(SHELL)"
	@echo "Python: $(PYTHON)"
	@echo "UV: $(UV)"