"""
Integration test setup: app factory, DB/cache/auth overrides, and HTTP client fixture.

This config avoids external services (Redis, OIDC server, Weaviate) and uses
an in-memory SQLite database via a patched register_tortoise.
"""
from __future__ import annotations

import asyncio
import os
from contextlib import AbstractAsyncContextManager
from typing import AsyncIterator, Callable

import pytest
from httpx import AsyncClient
from unittest.mock import patch


# Ensure test environment (some variables also come from tests/conftest.py)
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("TIMEZONE", "America/Sao_Paulo")


class _FakeRedis:
    def __init__(self, *args, **kwargs):
        pass

    async def ping(self):
        return True


def _patched_register_tortoise_sqlite(*args, **kwargs) -> AbstractAsyncContextManager:
    """A lightweight replacement for app.utils.register_tortoise using SQLite in-memory."""
    from tortoise import Tortoise, connections

    class _Manager(AbstractAsyncContextManager):
        async def __aenter__(self):
            await Tortoise.init(
                db_url="sqlite://:memory:", modules={"app": ["app.models"]}
            )
            # Auto-generate schemas for tests
            await Tortoise.generate_schemas()
            return self

        async def __aexit__(self, *exc):
            await connections.close_all()

    return _Manager()


@pytest.fixture(scope="session")
def app_instance():
    """Create the FastAPI app with critical patches applied before import."""
    # Patch external services before importing app.main so module-level side effects are neutralized
    redis_patcher = patch("redis.asyncio.Redis", _FakeRedis)
    cache_patcher = patch("fastapi_cache.FastAPICache.init", lambda *_args, **_kw: None)
    weaviate_schema_patcher = patch("app.utils.create_update_weaviate_schema", lambda: None)
    # Crucially: patch register_tortoise in app.utils BEFORE app.main imports it
    tortoise_reg_patcher = patch("app.utils.register_tortoise", _patched_register_tortoise_sqlite)

    for p in (redis_patcher, cache_patcher, weaviate_schema_patcher, tortoise_reg_patcher):
        p.start()

    # Import the app only after patches
    from app.main import app  # type: ignore
    from app.oidc import get_current_user
    from app.pydantic_models import OIDCUser

    # Override OIDC dependency with a static test user
    def _fake_current_user():
        # Minimal valid user payload
        return OIDCUser(
            sub="test-user-id",
            nickname="test.user",
            name="Test User",
            email="test.user@example.com",
            groups=[
                os.getenv("AUTH_PROVIDER_GROUP_USER", "civitas"),
            ],
            cpf="11144477735",
            matricula="000000",
            orgao="SMDE",
            setor="TI",
        )

    app.dependency_overrides[get_current_user] = _fake_current_user  # type: ignore

    yield app

    # Stop patches after session
    for p in (redis_patcher, cache_patcher, weaviate_schema_patcher, tortoise_reg_patcher):
        p.stop()


@pytest.fixture
async def client(app_instance):
    """HTTP client bound to the ASGI app with lifespan enabled."""
    async with AsyncClient(app=app_instance, base_url="http://test") as ac:
        yield ac
# -*- coding: utf-8 -*-
import os
import asyncio
from typing import AsyncGenerator
from unittest.mock import patch, AsyncMock

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Mock environment variables early
os.environ.update({
    "ENVIRONMENT": "test",
    "DATABASE_URL": "sqlite:///:memory:",
    "REDIS_HOST": "localhost",
    "REDIS_PORT": "6379",
    "REDIS_DB": "0",
    "REDIS_PASSWORD": "",
    "LOG_LEVEL": "WARNING",
    "SENTRY_ENABLE": "false",
    "RATE_LIMIT_DEFAULT": "1000/minute",
    "OIDC_BASE_URL": "http://test-auth.localhost",
    "OIDC_CLIENT_ID": "test-client",
    "OIDC_CLIENT_SECRET": "test-secret",
    "SECRET_KEY": "test-secret-key",
    "ALLOWED_ORIGINS": "*",
    "ALLOWED_METHODS": "*",
    "ALLOWED_HEADERS": "*",
    "ALLOW_CREDENTIALS": "true",
    "DATA_RELAY_PUBLISH_TOKEN": "test-token",
    "CORTEX_API_URL": "http://test-cortex.localhost",
    "CORTEX_USERNAME": "test-user",
    "CORTEX_PASSWORD": "test-pass",
})

# Mock Redis operations
with patch('redis.asyncio.Redis') as mock_redis_class:
    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True
    mock_redis_class.return_value = mock_redis
    
    # Mock FastAPI Cache
    with patch('fastapi_cache.FastAPICache.init'):
        # Mock HTTP requests for health checks
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.raise_for_status.return_value = None
            mock_client.get.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client
            
            # Import the app after mocking
            from app.main import app


@pytest.fixture
def test_client():
    """Synchronous test client for simple endpoint tests."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async test client for integration tests."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    with patch('redis.asyncio.Redis') as mock_redis_class:
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_redis_class.return_value = mock_redis
        yield mock_redis


@pytest.fixture
def mock_auth_client():
    """Mock authentication service responses."""
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_cortex_api():
    """Mock Cortex API responses for plate queries."""
    with patch('app.utils.cortex_request') as mock_cortex:
        async def mock_cortex_response(*args, **kwargs):
            return True, {
                "placa": "ABC1234",
                "nomeProprietario": "Test Owner",
                "municipioPlaca": "Rio de Janeiro",
                "ufEmplacamento": "RJ",
            }
        mock_cortex.side_effect = mock_cortex_response
        yield mock_cortex


@pytest.fixture
def sample_plate_data():
    """Sample plate data for testing."""
    return {
        "plate": "ABC1234",
        "owner": "Test Owner",
        "city": "Rio de Janeiro",
        "state": "RJ",
    }


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "full_name": "Test User",
        "cpf": "12345678900",
    }


@pytest.fixture
async def authenticated_headers():
    """Mock authentication headers for protected endpoints."""
    return {
        "Authorization": "Bearer test-token",
        "Content-Type": "application/json",
    }


# Configure asyncio for tests
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()