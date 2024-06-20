# -*- coding: utf-8 -*-
import sys
from contextlib import asynccontextmanager

import orjson as json
import sentry_sdk
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_pagination import add_pagination
from httpx import AsyncClient
from loguru import logger
from redis.asyncio import Redis
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.responses import JSONResponse

from app import config
from app.db import TORTOISE_ORM
from app.oidc import AuthError
from app.pydantic_models import HealthCheck
from app.rate_limiter import limiter
from app.routers import auth, cars, users
from app.utils import register_tortoise

logger.remove()
logger.add(sys.stdout, level=config.LOG_LEVEL)

if config.SENTRY_ENABLE:
    sentry_sdk.init(
        dsn=config.SENTRY_DSN,
        traces_sample_rate=0,
        environment=config.SENTRY_ENVIRONMENT,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Register tortoise manually as it doesn't support lifespan
    async with register_tortoise(
        app, config=TORTOISE_ORM, generate_schemas=False, add_exception_handlers=True
    ):
        yield

    # Run things on shutdown
    logger.info("Shutting down...")
    # Do things here
    logger.info("Shutdown complete")


app = FastAPI(
    title="CIVITAS API",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

logger.debug("Configuring CORS with the following settings:")
allow_origins = config.ALLOWED_ORIGINS if config.ALLOWED_ORIGINS else ()
logger.debug(f"ALLOWED_ORIGINS: {allow_origins}")
allow_origin_regex = config.ALLOWED_ORIGINS_REGEX if config.ALLOWED_ORIGINS_REGEX else None
logger.debug(f"ALLOWED_ORIGINS_REGEX: {allow_origin_regex}")
logger.debug(f"ALLOWED_METHODS: {config.ALLOWED_METHODS}")
logger.debug(f"ALLOWED_HEADERS: {config.ALLOWED_HEADERS}")
logger.debug(f"ALLOW_CREDENTIALS: {config.ALLOW_CREDENTIALS}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_origin_regex=allow_origin_regex,
    allow_methods=config.ALLOWED_METHODS,
    allow_headers=config.ALLOWED_HEADERS,
    allow_credentials=config.ALLOW_CREDENTIALS,
)

app.include_router(auth.router)
app.include_router(cars.router)
app.include_router(users.router)


add_pagination(app)


FastAPICache.init(
    RedisBackend(
        Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            db=config.REDIS_DB,
            password=config.REDIS_PASSWORD,
        )
    )
)


@app.get(
    "/health",
    tags=["Healthcheck"],
    summary="Performs a health check",
    responses={
        200: {"status": "OK"},
        429: {"error": "Rate limit exceeded"},
        503: {"status": "Service Unavailable"},
    },
    response_model=HealthCheck,
)
@limiter.limit(config.RATE_LIMIT_DEFAULT)
async def healthcheck(request: Request):
    # Check if Redis is available
    try:
        r = Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            db=config.REDIS_DB,
            password=config.REDIS_PASSWORD,
        )
        await r.ping()
    except Exception as exc:
        logger.error(f"Failed to ping Redis: {exc}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=json.dumps({"status": "Service Unavailable"}),
        )
    # Check if authentik is available
    try:
        async with AsyncClient(timeout=None) as client:
            response = await client.get(f"{config.OIDC_BASE_URL}/-/health/live/")
            response.raise_for_status()
            assert response.status_code == 204
            response = await client.get(f"{config.OIDC_BASE_URL}/-/health/ready/")
            response.raise_for_status()
            assert response.status_code == 204
    except Exception as exc:
        logger.warning(f"Failed to ping authentik: {exc}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=json.dumps({"status": "Service Unavailable"}),
        )
    return {"status": "OK"}


@app.exception_handler(AuthError)
def handle_auth_error(request: Request, ex: AuthError):
    return JSONResponse(status_code=ex.status_code, content=ex.error)


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(request: Request, ex: RequestValidationError):
    logger.error(f"RequestValidationError: {ex.errors()}")
    content = {"detail": ex.errors()}
    return JSONResponse(content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
