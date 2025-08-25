import os
import pytest
from unittest.mock import patch, MagicMock

# Mock urlopen before any imports to prevent HTTP requests
def mock_urlopen_response(*args, **kwargs):
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"keys": []}'  # Mock JWKS response
    return mock_response

# Apply the mock before importing any app modules
patch('urllib.request.urlopen', side_effect=mock_urlopen_response).start()

# Set environment variables for testing before any imports
os.environ.update({
    # Test environment
    "ENVIRONMENT": "test",
    
    # Basic required variables
    "DATABASE_URL": "sqlite:///:memory:",
    "REDIS_URL": "redis://localhost:6379",
    "SECRET_KEY": "test-secret-key-for-testing-only",
    "TIMEZONE": "America/Sao_Paulo",
    
    # OIDC configuration (required by base config)
    "OIDC_BASE_URL": "https://test-oidc.com",
    "OIDC_CLIENT_ID": "test-client-id",
    "OIDC_CLIENT_SECRET": "test-client-secret",
    "OIDC_ISSUER_URL": "https://test-oidc.com/.well-known/openid_configuration",
    "OIDC_TOKEN_URL": "https://test-oidc.com/token",
    "OIDC_GET_USER_TOKEN_CACHE_TTL": "2700",
    
    # Auth groups
    "AUTH_PROVIDER_GROUP_ADMIN": "civitas-admin",
    "AUTH_PROVIDER_GROUP_USER": "civitas",
    "AUTH_PROVIDER_GROUP_AGENT": "civitas-agent",
    
    # Google Cloud Platform
    "GOOGLE_BIGQUERY_PAGE_SIZE": "100",
    "GOOGLE_MAPS_API_KEY": "test-google-maps-key",
    "GOOGLE_MAPS_API_MAX_POINTS_PER_REQUEST": "27",
    "GCP_SERVICE_ACCOUNT_CREDENTIALS": "eyJ0ZXN0IjogdHJ1ZX0=",  # base64 of {"test": true}
    
    # Cache settings
    "CACHE_CAR_PATH_TTL": "600",
    "CACHE_CAR_POSITIONS_TTL": "600",
    "CACHE_CAR_HINTS_TTL": "600",
    "CACHE_RADAR_POSITIONS_TTL": "86400",
    "CACHE_WAZE_ALERTS_TTL": "300",
    "CACHE_CAR_BY_RADAR_TTL": "300",
    "CACHE_CAMERAS_COR_TTL": "300",
    "CACHE_FOGOCRUZADO_TTL": "300",
    "CACHE_MONITORED_PLATES_HISTORY_TTL": "300",
    "CACHE_REPORTS_METADATA_TTL": "900",
    
    # Data Relay
    "DATA_RELAY_BASE_URL": "https://test-data-relay.com",
    "DATA_RELAY_USERNAME": "test-user",
    "DATA_RELAY_PASSWORD": "test-password",
    "DATA_RELAY_PUBLISH_TOKEN": "test-publish-token",
    
    # Fogo Cruzado
    "FOGOCRUZADO_USERNAME": "test-fogo-user",
    "FOGOCRUZADO_PASSWORD": "test-fogo-password",
    
    # Cortex API
    "CORTEX_USERNAME": "test-cortex-user",
    "CORTEX_PASSWORD": "test-cortex-password",
    "CORTEX_CPF_RATE_LIMIT": "2/minute",
    
    # API related
    "CORTEX_PESSOAS_BASE_URL": "http://test-api.com",
    "CORTEX_VEICULOS_BASE_URL": "http://test-api.com",
    "WEAVIATE_BASE_URL": "http://test-weaviate.com",
    "WEAVIATE_SCHEMA_CLASS": "TestClass",
    "FOGOCRUZADO_BASE_URL": "http://test-fogocruzado.com",
    "TIXXI_CAMERAS_LIST_URL": "http://test-tixxi.com",
    
    # Embeddings
    "EMBEDDINGS_SOURCE_TABLE": "test.embeddings",
    "EMBEDDINGS_SOURCE_TABLE_ID_COLUMN": "id",
    "EMBEDDINGS_SOURCE_TABLE_SOURCE_COLUMN": "source",
    "EMBEDDINGS_SOURCE_TABLE_TEXT_COLUMN": "text",
    "EMBEDDINGS_SOURCE_TABLE_TIMESTAMP_COLUMN": "timestamp",
    "EMBEDDINGS_SOURCE_TABLE_REPORT_TIMESTAMP_COLUMN": "report_timestamp",
    "UPDATE_EMBEDDINGS_LOCK_TIMEOUT": "86400",
    "UPDATE_EMBEDDINGS_BATCH_SIZE": "100",
    "UPDATE_EMBEDDINGS_DEBUG_DISCORD_WEBHOOK": "https://discord.com/api/webhooks/test",
    
    # Rate limiting
    "RATE_LIMIT_DEFAULT": "100/minute",
    
    # Logging
    "LOG_LEVEL": "INFO",
})

# Additional fixture for any tests that need it
@pytest.fixture(autouse=True)
def mock_urlopen_fixture():
    """Additional urlopen mock fixture for tests."""
    # The main mock is already applied globally above
    yield


@pytest.fixture(autouse=True)
def setup_test_config():
    """Set up test configuration that bypasses Infisical."""
    # This will run before each test
    yield