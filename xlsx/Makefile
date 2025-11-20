.PHONY: help install test build run stop clean logs health templates

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install Python dependencies
	pip install -r requirements.txt

test: ## Run tests
	pytest tests/ -v

build: ## Build Docker image
	docker-compose build

run: ## Start the service with Docker Compose
	docker-compose up -d
	@echo "Service starting..."
	@echo "Wait a few seconds, then check: make health"

stop: ## Stop the service
	docker-compose down

restart: ## Restart the service
	docker-compose restart

clean: ## Stop service and remove volumes
	docker-compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

logs: ## Show service logs
	docker-compose logs -f xlsx-service

health: ## Check service health
	@curl -s http://localhost:8000/health | python -m json.tool || echo "Service not responding"

templates: ## List available templates
	@curl -s http://localhost:8000/templates | python -m json.tool || echo "Service not responding"

dev: ## Run in development mode (local)
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

example: ## Run example usage script
	python example_usage.py

map: ## Run template mapper (usage: make map TEMPLATE=path/to/template.xlsx)
	@if [ -z "$(TEMPLATE)" ]; then \
		echo "Usage: make map TEMPLATE=path/to/template.xlsx"; \
		exit 1; \
	fi
	python template_mapper.py $(TEMPLATE)
