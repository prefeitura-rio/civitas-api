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
	@echo "  mock-api         Start diagnostic mock API (port 8001)"
	@echo ""
	@echo "📊 DIAGNOSTIC Scripts (métricas + console output):"
	@echo "  diag-eventloop   Event loop lag measurement"
	@echo "  diag-load        Load testing against mock API"
	@echo "  diag-all         All diagnostic scripts"
	@echo ""
	@echo "✅ PERFORMANCE Tests (pytest + assertions):"
	@echo "  test-perf        All performance tests with assertions"
	@echo "  test-perf-fast   Fast event loop test only"
	@echo "  test-examples    Show failing test examples"
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

# 📊 DIAGNOSTIC Scripts (collect metrics + print results)
diag-eventloop:
	@echo "� Running Event Loop Diagnostic..."
	poetry run python tests/diagnostic/quick_test.py

mock-api:
	@echo "🚀 Starting Diagnostic Mock API on port 8001..."
	@echo "Press Ctrl+C to stop"
	poetry run python tests/diagnostic/mock_api.py

diag-load:
	@echo "📊 Running Load Testing Diagnostic..."
	@echo "Note: This requires mock API running on port 8001"
	@echo "Run 'make mock-api' in another terminal first"
	poetry run python tests/diagnostic/load_test.py

diag-all:
	@echo "🔄 Running All Diagnostic Scripts..."
	@make diag-eventloop
	@echo ""
	@echo "⚠️  Next: Start mock API with 'make mock-api' and run 'make diag-load'"

# ✅ PERFORMANCE Tests (pytest with assertions that can pass/fail)
test-perf:
	@echo "✅ Running Performance Tests with pytest..."
	@echo "These tests have assertions and can PASS/FAIL"
	poetry run pytest tests/performance/test_performance_real.py -v

test-perf-fast:
	@echo "⚡ Running fast performance test..."
	poetry run pytest tests/performance/test_performance_real.py::test_event_loop_lag_within_limits -v

test-examples:
	@echo "📝 Running test examples (some will fail intentionally)..."
	poetry run pytest tests/performance/test_examples.py -v
	@echo "🔄 Running All Performance Tests..."
	@make test-eventloop
	@echo ""
	@echo "⚠️  Next: Start test API with 'make test-api-mock' and run 'make test-performance'"

# Test real API (requires main API running)
test-real:
	@echo "🎯 Testing Real API Endpoints..."
	@echo "Note: This requires main API running on port 8000"
	@echo "Run 'make serve' in another terminal first"
	poetry run python -c "import asyncio; from tests.diagnostic.load_test import test_real_api; asyncio.run(test_real_api())"
