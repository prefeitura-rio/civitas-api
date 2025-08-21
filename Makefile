# Makefile para Civitas API - Performance Testing

.PHONY: help install lint serve test test-eventloop test-api-mock test-performance test-all-performance

help:
	@echo "Civitas API - Performance Testing Commands"
	@echo "=========================================="
	@echo ""
	@echo "Setup:"
	@echo "  install          Install dependencies using Poetry"
	@echo "  lint             Run code formatting and linting"
	@echo ""
	@echo "API:"
	@echo "  serve            Start main API (port 8080)"
	@echo "  test-api-mock    Start test API mock (port 8001)"
	@echo ""
	@echo "Performance Tests:"
	@echo "  test-eventloop   Run basic event loop tests"
	@echo "  test-performance Run load tests against mock API"
	@echo "  test-all         Run all performance tests"
	@echo ""
	@echo "Standard Tests:"
	@echo "  test             Run pytest tests"

install:
	poetry install

lint:
	poetry run black .
	poetry run isort .
	poetry run flake8 .

serve:
	poetry run uvicorn app.main:app --reload --port 8080

test:
	poetry run pytest

# Performance testing scripts
test-eventloop:
	@echo "🔍 Running Event Loop Tests..."
	poetry run python tests/quick_test.py

test-api-mock:
	@echo "🚀 Starting Test API Mock on port 8001..."
	@echo "Press Ctrl+C to stop"
	poetry run python tests/test_api.py

test-performance:
	@echo "📊 Running Performance Tests..."
	@echo "Note: This requires test API running on port 8001"
	@echo "Run 'make test-api-mock' in another terminal first"
	poetry run python tests/load_test.py

test-all:
	@echo "🔄 Running All Performance Tests..."
	@make test-eventloop
	@echo ""
	@echo "⚠️  Next: Start test API with 'make test-api-mock' and run 'make test-performance'"

# Test real API (requires main API running)
test-real:
	@echo "🎯 Testing Real API Endpoints..."
	@echo "Note: This requires main API running on port 8000"
	@echo "Run 'make serve' in another terminal first"
	poetry run python -c "import asyncio; from tests.load_test import test_real_api; asyncio.run(test_real_api())"
