.PHONY: help install install-dev format lint check clean test

help:  ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

install:  ## Install production dependencies
	pip install -e .

install-dev:  ## Install development dependencies  
	pip install -e ".[dev]"

format:  ## Format code with Black
	black src/ test_langgraph.py test_api_key.py

lint:  ## Lint code with Ruff
	ruff check src/ test_langgraph.py test_api_key.py

type-check:  ## Type check code with mypy
	mypy src/ test_langgraph.py test_api_key.py

check: format lint type-check  ## Format, lint, and type check code

clean:  ## Clean up cache files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".DS_Store" -delete

test:  ## Run the test script
	python test_langgraph.py --folder ./sample_docs --request "All emails about Project Blue Sky"