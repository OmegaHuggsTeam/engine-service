.PHONY: install install-dev init test test-fast test-cov lint format check \
       docker-up docker-down gateway webhook clean validate benchmark help

# Default Python
PYTHON ?= python
PIP ?= pip

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install core dependencies
	$(PIP) install -r requirements.txt

install-dev: ## Install all dependencies including dev tools
	$(PIP) install -r requirements.txt
	$(PIP) install ruff black mypy pytest-cov

init: ## Run self-bootstrap (run_init.py)
	$(PYTHON) run_init.py

test: ## Run all tests
	$(PYTHON) -m pytest tests/ src/neural_link/tests/ -v --tb=short

test-fast: ## Run tests excluding slow/integration
	$(PYTHON) -m pytest tests/ src/neural_link/tests/ -v --tb=short -m "not slow and not integration and not e2e" -x

test-cov: ## Run tests with coverage report
	$(PYTHON) -m pytest tests/ src/neural_link/tests/ \
		--cov=src --cov-report=xml --cov-report=term-missing \
		--tb=short -q

lint: ## Run linters (ruff + black check)
	ruff check src/ tests/ automation_hub/ || true
	black --check --diff src/ tests/ automation_hub/ || true

format: ## Auto-format code (ruff + black)
	ruff check --fix src/ tests/ automation_hub/ || true
	black src/ tests/ automation_hub/

check: lint test ## Run lint + tests (CI equivalent)

docker-up: ## Start Docker services (Neo4j)
	docker compose up -d

docker-down: ## Stop Docker services
	docker compose down

gateway: ## Start Sovereign Gateway (port 8766)
	$(PYTHON) -m uvicorn src.neural_link.api.sovereign_gateway:app --host 0.0.0.0 --port 8766 --reload

webhook: ## Start Webhook Listener (port 8765)
	$(PYTHON) -m uvicorn automation_hub.bridge.webhook_listener:app --host 0.0.0.0 --port 8765 --reload

clean: ## Remove caches and build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -f coverage.xml .coverage
	rm -rf htmlcov/

validate: ## Validate core imports work
	$(PYTHON) -c "from src.utils.llm_client import LLMClient; print('LLMClient OK')"
	$(PYTHON) -c "from src.agents.agent_factory import AgentFactory; print('AgentFactory OK')"
	$(PYTHON) -c "from src.neural_link.api.sovereign_gateway import app; print('Gateway OK')"
	@echo "All core imports validated."

benchmark: ## Run pipeline benchmark (offline, mocked LLM)
	$(PYTHON) tools/benchmark_pipeline.py
