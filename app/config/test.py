# -*- coding: utf-8 -*-
"""Test configuration that mocks external dependencies and provides safe defaults."""

import os
from pathlib import Path
from . import getenv_list_or_action, getenv_or_action
# Don't import from base to avoid environment variable loading

# Environment
environment = "test"

# Logging
LOG_LEVEL = "DEBUG"

# Timezone configuration
TIMEZONE = "America/Sao_Paulo"

# Sentry (disabled for tests)
SENTRY_ENABLE = False
SENTRY_DSN = None
SENTRY_ENVIRONMENT = None

# OIDC (mocked for tests)
OIDC_BASE_URL = "http://localhost:8000/auth"
OIDC_CLIENT_ID = "test-client-id"
OIDC_CLIENT_SECRET = "test-client-secret"
OIDC_ISSUER_URL = "http://localhost:8000/auth/realms/test"
OIDC_TOKEN_URL = "http://localhost:8000/auth/realms/test/protocol/openid-connect/token"
OIDC_GET_USER_TOKEN_CACHE_TTL = 60

# Mock JWKS response for testing
JWS = {"keys": []}

# Auth provider groups
AUTH_PROVIDER_GROUP_ADMIN = "test-admin"
AUTH_PROVIDER_GROUP_USER = "test-user"
AUTH_PROVIDER_GROUP_AGENT = "test-agent"

# Database configuration (use test database)
DATABASE_HOST = getenv_or_action("TEST_DATABASE_HOST", default="localhost")
DATABASE_PORT = getenv_or_action("TEST_DATABASE_PORT", default="5432")
DATABASE_USER = getenv_or_action("TEST_DATABASE_USER", default="postgres")
DATABASE_PASSWORD = getenv_or_action("TEST_DATABASE_PASSWORD", default="postgres")
DATABASE_NAME = getenv_or_action("TEST_DATABASE_NAME", default="civitas_test")

# CORS configuration
ALLOWED_ORIGINS = ["*"]
ALLOWED_ORIGINS_REGEX = None
ALLOWED_METHODS = ["*"]
ALLOWED_HEADERS = ["*"]
ALLOW_CREDENTIALS = True

# Redis configuration (use test Redis)
REDIS_HOST = getenv_or_action("TEST_REDIS_HOST", default="localhost")
REDIS_PORT = getenv_or_action("TEST_REDIS_PORT", default="6379")
REDIS_DB = getenv_or_action("TEST_REDIS_DB", default="1")  # Different DB for tests
REDIS_PASSWORD = getenv_or_action("TEST_REDIS_PASSWORD", default="")

# Rate limits (more permissive for tests)
RATE_LIMIT_DEFAULT = "10000/second"

# Google Cloud Platform configuration (mocked)
GOOGLE_BIGQUERY_PAGE_SIZE = 100
GOOGLE_MAPS_API_KEY = "test-google-maps-api-key"
GOOGLE_MAPS_API_MAX_POINTS_PER_REQUEST = 27
GCP_SERVICE_ACCOUNT_CREDENTIALS = '{"type": "service_account", "project_id": "test-project"}'

# Cache configuration (shorter TTLs for tests)
CACHE_CAR_PATH_TTL = 10
CACHE_CAR_POSITIONS_TTL = 10
CACHE_CAR_HINTS_TTL = 10
CACHE_RADAR_POSITIONS_TTL = 60
CACHE_WAZE_ALERTS_TTL = 10
CACHE_CAR_BY_RADAR_TTL = 10
CACHE_CAMERAS_COR_TTL = 10
CACHE_FOGOCRUZADO_TTL = 10
CACHE_MONITORED_PLATES_HISTORY_TTL = 10
CACHE_REPORTS_METADATA_TTL = 10

# Data Relay configuration (mocked)
DATA_RELAY_BASE_URL = "http://localhost:8001/test-data-relay"
DATA_RELAY_USERNAME = "test-relay-user"
DATA_RELAY_PASSWORD = "test-relay-password"
DATA_RELAY_PUBLISH_TOKEN = "test-relay-token"

# Fogo Cruzado API configuration (mocked)
FOGOCRUZADO_BASE_URL = "http://localhost:8002/test-fogocruzado"
FOGOCRUZADO_USERNAME = "test-fogocruzado-user"
FOGOCRUZADO_PASSWORD = "test-fogocruzado-password"

# Cortex API configuration (mocked)
CORTEX_PESSOAS_BASE_URL = "http://localhost:8003/test-cortex-pessoas"
CORTEX_VEICULOS_BASE_URL = "http://localhost:8004/test-cortex-veiculos"
CORTEX_USERNAME = "test-cortex-user"
CORTEX_PASSWORD = "test-cortex-password"
CORTEX_CPF_RATE_LIMIT = "1000/minute"  # More permissive for tests

# Tixxi (mocked)
TIXXI_CAMERAS_LIST_URL = "http://localhost:8005/test-tixxi-cameras"

# Weaviate schema (test configuration)
WEAVIATE_SCHEMA_CLASS = "TestOccurrence"
WEAVIATE_SCHEMA = {
    "class": WEAVIATE_SCHEMA_CLASS,
    "vectorizer": "none",
    "properties": [
        {"name": "id_report", "dataType": ["text"]},
        {"name": "id_source", "dataType": ["text"]},
        {"name": "id_report_original", "dataType": ["text"]},
        {"name": "data_report", "dataType": ["date"]},
        {"name": "data_report_seconds", "dataType": ["number"]},
        {"name": "report_data_raw", "dataType": ["text"]},
        {"name": "orgaos", "dataType": ["text[]"]},
        {"name": "categoria", "dataType": ["text"]},
        {
            "name": "tipo_subtipo",
            "dataType": ["object[]"],
            "nestedProperties": [
                {"name": "tipo", "dataType": ["text"]},
                {"name": "subtipo", "dataType": ["text[]"]},
            ],
        },
        {"name": "descricao", "dataType": ["text"]},
        {"name": "logradouro", "dataType": ["text"]},
        {"name": "numero_logradouro", "dataType": ["text"]},
        {"name": "latitude", "dataType": ["number"]},
        {"name": "longitude", "dataType": ["number"]},
        {"name": "updated_at", "dataType": ["date"]},
        {"name": "updated_at_seconds", "dataType": ["number"]},
    ],
}

# Update embeddings configuration (test values)
EMBEDDINGS_SOURCE_TABLE = "test.test_reports"
EMBEDDINGS_SOURCE_TABLE_ID_COLUMN = "id_report"
EMBEDDINGS_SOURCE_TABLE_SOURCE_COLUMN = "id_source"
EMBEDDINGS_SOURCE_TABLE_TEXT_COLUMN = "descricao"
EMBEDDINGS_SOURCE_TABLE_TIMESTAMP_COLUMN = "updated_at"
EMBEDDINGS_SOURCE_TABLE_REPORT_TIMESTAMP_COLUMN = "data_report"

UPDATE_EMBEDDINGS_LOCK_TIMEOUT = 60
UPDATE_EMBEDDINGS_BATCH_SIZE = 10

UPDATE_EMBEDDINGS_DEBUG_DISCORD_WEBHOOK = "http://localhost:8006/test-discord-webhook"

# Embeddings API configuration (test)
EMBEDDING_API_BASE_URL = "http://localhost:8007/test-embeddings"

# Weaviate configuration (test)
WEAVIATE_BASE_URL = "http://localhost:8008/test-weaviate"

# Discord webhook (test)
DISCORD_WEBHOOK_DEBUG = "http://localhost:8009/test-discord-debug"

# Data CSV URL (test)
DATA_CODCET_TO_CAMERA_NUMERO_CSV_URL = "http://localhost:8010/test-csv-data"

# Assets directory (same as production)
ASSETS_DIR = Path(__file__).parent.parent / "assets"

# Vehicle types mapping (same as production)
VEHICLE_TYPES_MAPPING = {
    "automovel": "automovel",
    "AUTOMÓVEL": "automovel",
    "ciclomotor": "ciclomotor",
    "indefinido": "indefinido",
    "INDEFINIDO": "indefinido",
    "onibus": "onibus",
    "ÔNIBUS": "onibus",
    "caminhao": "caminhao",
    "CAMINHÃO": "caminhao",
    "MOTO": "moto",
    "CAMINHÃO / ÔNIBUS": "caminhao_onibus",
}

# PDF report paths (same as production)
HTML_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
STYLES_BASE_PATH = HTML_TEMPLATES_DIR / "styles_base.css"
