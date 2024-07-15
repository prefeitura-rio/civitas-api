# -*- coding: utf-8 -*-
from urllib.request import urlopen

import orjson as json

from . import getenv_list_or_action, getenv_or_action

# Logging
LOG_LEVEL = getenv_or_action("LOG_LEVEL", default="INFO")

# Timezone configuration
TIMEZONE = "America/Sao_Paulo"

# Sentry
SENTRY_ENABLE = False
SENTRY_DSN = None
SENTRY_ENVIRONMENT = None

# OIDC
OIDC_BASE_URL = getenv_or_action("OIDC_BASE_URL").rstrip("/")
OIDC_CLIENT_ID = getenv_or_action("OIDC_CLIENT_ID")
OIDC_CLIENT_SECRET = getenv_or_action("OIDC_CLIENT_SECRET")
OIDC_ISSUER_URL = getenv_or_action("OIDC_ISSUER_URL")
OIDC_TOKEN_URL = getenv_or_action("OIDC_TOKEN_URL")
OIDC_GET_USER_TOKEN_CACHE_TTL = int(
    getenv_or_action("OIDC_GET_USER_TOKEN_CACHE_TTL", default=60 * 45)
)
jwksurl = urlopen(OIDC_ISSUER_URL + "/jwks/")
JWS = json.loads(jwksurl.read())

# Auth provider groups
AUTH_PROVIDER_GROUP_ADMIN = getenv_or_action("AUTH_PROVIDER_GROUP_ADMIN", default="civitas-admin")
AUTH_PROVIDER_GROUP_USER = getenv_or_action("AUTH_PROVIDER_GROUP_USER", default="civitas")

# Google Cloud Platform configuration
GOOGLE_BIGQUERY_PAGE_SIZE = getenv_or_action("GOOGLE_BIGQUERY_PAGE_SIZE", default=100)
GOOGLE_MAPS_API_KEY = getenv_or_action("GOOGLE_MAPS_API_KEY")
GOOGLE_MAPS_API_MAX_POINTS_PER_REQUEST = getenv_or_action(
    "GOOGLE_MAPS_API_MAX_POINTS_PER_REQUEST", default=27
)

# Cache configuration
CACHE_CAR_PATH_TTL = int(getenv_or_action("CACHE_CAR_PATH_TTL", default=60 * 10))
CACHE_CAR_POSITIONS_TTL = int(getenv_or_action("CACHE_CAR_POSITIONS_TTL", default=60 * 10))
CACHE_CAR_HINTS_TTL = int(getenv_or_action("CACHE_CAR_HINTS_TTL", default=60 * 10))

# RBAC configuration
RBAC_EXCLUDED_PATHS = getenv_list_or_action("RBAC_EXCLUDED_PATHS")
RBAC_PERMISSIONS_CACHE_TTL = int(getenv_or_action("RBAC_PERMISSIONS_CACHE_TTL", default=60 * 5))

# Data Relay configuration
DATA_RELAY_BASE_URL = getenv_or_action("DATA_RELAY_BASE_URL").rstrip("/")
DATA_RELAY_USERNAME = getenv_or_action("DATA_RELAY_USERNAME")
DATA_RELAY_PASSWORD = getenv_or_action("DATA_RELAY_PASSWORD")
DATA_RELAY_PUBLISH_TOKEN = getenv_or_action("DATA_RELAY_PUBLISH_TOKEN")

# Tixxi
TIXXI_CAMERAS_LIST_URL = getenv_or_action("TIXXI_CAMERAS_LIST_URL")
