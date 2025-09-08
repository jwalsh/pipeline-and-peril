# Pipeline & Peril - Makefile
# Uses GNU Make (gmake) features

.PHONY: help setup-env dev test clean publish-readme all

# Default target
help:
	@echo "Pipeline & Peril - Development Tasks"
	@echo ""
	@echo "Available targets:"
	@echo "  setup        - Complete project setup (generates README.md, installs deps)"
	@echo "  setup-env    - Initialize Python environment with uv"
	@echo "  dev          - Install development dependencies"
	@echo "  test         - Run tests"
	@echo "  clean        - Remove generated files and cache"
	@echo "  publish-readme - Generate README.md from README.org using Emacs"
	@echo ""

# Non-phony target for README.md generation
README.md: README.org
	@echo "Generating README.md from README.org..."
	@emacs --batch \
		--eval "(require 'org)" \
		--eval "(setq org-export-with-toc t)" \
		--eval "(setq org-export-with-author t)" \
		--eval "(setq org-export-with-email nil)" \
		--eval "(find-file \"README.org\")" \
		--eval "(org-md-export-to-markdown)" \
		--kill
	@echo "README.md generated successfully"

# Complete setup including README.md generation
setup: README.md setup-env
	@echo "Setup complete!"

# Initialize Python environment
setup-env:
	@echo "Initializing Python environment with uv..."
	@uv venv
	@uv pip install -e .
	@echo "Python environment ready"

# Install development dependencies
dev:
	@echo "Installing development dependencies..."
	@uv pip install -e ".[dev]"
	@echo "Development dependencies installed"

# Run tests
test:
	@echo "Running tests..."
	@uv run pytest tests/ -v

# Clean generated files and cache
clean:
	@echo "Cleaning generated files..."
	@rm -f README.md
	@rm -rf __pycache__
	@rm -rf .pytest_cache
	@rm -rf .coverage
	@rm -rf htmlcov
	@rm -rf dist
	@rm -rf *.egg-info
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*~" -delete
	@echo "Clean complete"

# Generate README.md explicitly
publish-readme: README.md

# Build all documentation
all: setup