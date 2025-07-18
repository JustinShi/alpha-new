# Alpha Trading System - Development Makefile
#
# This Makefile provides convenient commands for development tasks
# Make sure you have poetry installed: pip install poetry

.PHONY: help install dev-install test lint format type-check clean build run docs pre-commit

# Default target
help: ## Show this help message
	@echo "Alpha Trading System - Development Commands"
	@echo "=========================================="
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Installation
install: ## Install production dependencies
	poetry install --only=main

dev-install: ## Install all dependencies including dev tools
	poetry install
	poetry run pre-commit install

# Code Quality
lint: ## Run linting with ruff
	poetry run ruff check .

lint-fix: ## Run linting with auto-fix
	poetry run ruff check --fix .

format: ## Format code with ruff
	poetry run ruff format .

type-check: ## Run type checking with mypy
	poetry run mypy src/

# Testing
test: ## Run tests
	poetry run pytest

test-cov: ## Run tests with coverage
	poetry run pytest --cov=src/alpha_new --cov-report=html --cov-report=term

test-fast: ## Run tests excluding slow tests
	poetry run pytest -m "not slow"

# Quality Checks (run all)
check: lint type-check test ## Run all quality checks

# Pre-commit
pre-commit: ## Run pre-commit hooks on all files
	poetry run pre-commit run --all-files

pre-commit-update: ## Update pre-commit hooks
	poetry run pre-commit autoupdate

# Cleaning
clean: ## Clean up build artifacts and cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ htmlcov/ .coverage

# Building
build: ## Build the package
	poetry build

# Running
run: ## Run the main application
	poetry run alpha-new

run-example: ## Run the token example
	poetry run alpha-token

# Development
dev: dev-install ## Set up development environment
	@echo "Development environment ready!"
	@echo "Run 'make help' to see available commands"

# Documentation (if you add docs later)
docs: ## Generate documentation (placeholder)
	@echo "Documentation generation not yet implemented"

# Docker (if you add Docker later)
docker-build: ## Build Docker image (placeholder)
	@echo "Docker build not yet implemented"

# Release (placeholder for future)
release: ## Create a new release (placeholder)
	@echo "Release process not yet implemented"
