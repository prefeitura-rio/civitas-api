from __future__ import annotations

import os
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport


os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("TIMEZONE", "America/Sao_Paulo")


class _FakeRedis:
    def __init__(self, *args, **kwargs):
        pass

    async def ping(self):
        return True
    
    def pipeline(self):
        return _FakeRedisPipeline()
    
    async def get(self, key):
        return None
    
    async def set(self, key, value, ex=None):
        return True
    
    async def incr(self, key):
        return 1
    
    async def expire(self, key, seconds):
        return True


class _FakeRedisPipeline:
    def __init__(self):
        pass
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def get(self, key):
        return self
    
    def incr(self, key):
        return self
    
    def expire(self, key, seconds):
        return self
    
    def set(self, key, value, ex=None):
        return self
    
    async def watch(self, key):
        # Mock watch method for Redis pipeline
        pass
    
    def multi(self):
        return self
    
    def unwatch(self):
        return self
    
    async def execute(self):
        return [None, 1, True]


@pytest.fixture(scope="session")
def app_instance():
    """Create the FastAPI app with patches applied before import."""
    redis_patcher = patch("redis.asyncio.Redis", _FakeRedis)
    cache_patcher = patch("fastapi_cache.FastAPICache.init", lambda *_args, **_kw: None)
    weaviate_schema_patcher = patch("app.utils.create_update_weaviate_schema", lambda: None)
    class _NoOpLimiter:
        def limit(self, *a, **k):
            def _decorator(func):
                return getattr(func, "__wrapped__", func)
            return _decorator
    limiter_patcher = patch("app.decorators.limiter", new=_NoOpLimiter())
    
    # Mock CPF rate limiter
    class _MockCPFRateLimiter:
        async def check(self, cpf: str) -> bool:
            return True  # Always allow requests in tests
    
    cpf_limiter_patcher = patch("app.utils.cpf_limiter", new=_MockCPFRateLimiter())
    
    for p in (
        redis_patcher,
        cache_patcher,
        weaviate_schema_patcher,
        limiter_patcher,
        cpf_limiter_patcher,
    ):
        p.start()

    # Import the app only after patches
    from app.main import app  # type: ignore
    from app.oidc import get_current_user
    from app.pydantic_models import OIDCUser
    # Patch limiter on app after import
    from app import main as app_main
    app_main.limiter = type("NoOpLimiter", (), {"limit": lambda *a, **k: (lambda f: f)})()
    app.state.limiter = app_main.limiter

    def _fake_current_user():
        now = 1_700_000_000
        return OIDCUser(
            iss="http://test-issuer",
            sub="test-user-id",
            aud="test-aud",
            exp=now + 3600,
            iat=now,
            auth_time=now,
            acr="level-1",
            azp="test-client",
            uid="test-uid",
            email="test.user@example.com",
            email_verified=True,
            name="Test User",
            given_name="Test",
            preferred_username="test.user",
            nickname="test.user",
            groups=[os.getenv("AUTH_PROVIDER_GROUP_USER", "civitas")],
            cpf="11144477735",
            matricula="000000",
            orgao="SMDE",
            setor="TI",
        )

    app.dependency_overrides[get_current_user] = _fake_current_user  # type: ignore
    yield app

    # Stop patches after session
    for p in (
        redis_patcher,
        cache_patcher,
        weaviate_schema_patcher,
        limiter_patcher,
        cpf_limiter_patcher,
    ):
        p.stop()


@pytest_asyncio.fixture
async def client(app_instance):
    """HTTP client bound to the ASGI app."""
    from tortoise import Tortoise, connections
    await Tortoise.init(db_url="sqlite://:memory:", modules={"app": ["app.models"]})
    await Tortoise.generate_schemas()
    transport = ASGITransport(app=app_instance)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    await connections.close_all()
