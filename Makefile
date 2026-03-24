# Makefile for Ampullary UI Development

.PHONY: help install install-dev build-resources clean test run lint format

help:  ## Display this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' Makefile | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install the package
	pip install .

install-dev:  ## Install the package in development mode  
	pip install -e .

build-resources:  ## Manually compile Qt resources
	python build_resources.py

clean:  ## Remove generated files and build artifacts
	rm -f ampullary_ui/*_rc.py
	rm -rf build/ dist/ *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

test:  ## Run tests (placeholder)
	@echo "No tests configured yet"

run:  ## Run the GUI application
	ampullary-gui

lint:  ## Run linting (placeholder)
	@echo "Linting not configured yet"

format:  ## Format code (placeholder)  
	@echo "Code formatting not configured yet"

# Development workflow targets
setup-dev: clean build-resources install-dev  ## Full development setup

rebuild: clean build-resources  ## Clean rebuild of resources