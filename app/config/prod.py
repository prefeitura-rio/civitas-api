# -*- coding: utf-8 -*-
from . import getenv_list_or_action, getenv_or_action
from .base import *  # noqa: F401, F403

# Logging
LOG_LEVEL = getenv_or_action("LOG_LEVEL", action="ignore", default="INFO")

# Database configuration
DATABASE_HOST = getenv_or_action("DATABASE_HOST", action="raise")
DATABASE_PORT = getenv_or_action("DATABASE_PORT", action="raise")
DATABASE_USER = getenv_or_action("DATABASE_USER", action="raise")
DATABASE_PASSWORD = getenv_or_action("DATABASE_PASSWORD", action="raise")
DATABASE_NAME = getenv_or_action("DATABASE_NAME", action="raise")

# Timezone configuration
if getenv_or_action("TIMEZONE", action="ignore"):
    TIMEZONE = getenv_or_action("TIMEZONE")

# CORS configuration
ALLOWED_ORIGINS = getenv_list_or_action("ALLOWED_ORIGINS", action="ignore")
ALLOWED_ORIGINS_REGEX = getenv_or_action("ALLOWED_ORIGINS_REGEX", action="ignore")
if not ALLOWED_ORIGINS and not ALLOWED_ORIGINS_REGEX:
    raise EnvironmentError("ALLOWED_ORIGINS or ALLOWED_ORIGINS_REGEX must be set.")
ALLOWED_METHODS = getenv_list_or_action("ALLOWED_METHODS", action="raise")
ALLOWED_HEADERS = getenv_list_or_action("ALLOWED_HEADERS", action="raise")
ALLOW_CREDENTIALS = (
    getenv_or_action("ALLOW_CREDENTIALS", action="raise").lower() == "true"
)

# Sentry
SENTRY_ENABLE = getenv_or_action("SENTRY_ENABLE", action="ignore").lower() == "true"
if SENTRY_ENABLE:
    SENTRY_DSN = getenv_or_action("SENTRY_DSN", action="raise")
    SENTRY_ENVIRONMENT = getenv_or_action("SENTRY_ENVIRONMENT", action="raise")

# Redis configuration
REDIS_HOST = getenv_or_action("REDIS_HOST", action="raise")
REDIS_PORT = getenv_or_action("REDIS_PORT", action="raise")
REDIS_DB = getenv_or_action("REDIS_DB", action="raise")
REDIS_PASSWORD = getenv_or_action("REDIS_PASSWORD", action="ignore")

# Rate limits
RATE_LIMIT_DEFAULT = getenv_or_action("RATE_LIMIT_DEFAULT", action="raise")

# Google Cloud configuration
GCP_SERVICE_ACCOUNT_CREDENTIALS = getenv_or_action(
    "GCP_SERVICE_ACCOUNT_CREDENTIALS", action="raise"
)

# feature flags
ENABLE_GCS_ENDPOINTS = getenv_or_action("ENABLE_GCS_ENDPOINTS", default="false").lower() == "true"
ENABLE_CLONING_REPORT_ENDPOINT = getenv_or_action("ENABLE_CLONING_REPORT_ENDPOINT", default="false").lower() == "true"
