# -*- coding: utf-8 -*-
from urllib.request import urlopen

import orjson as json

from . import getenv_or_action

# Logging
LOG_LEVEL = getenv_or_action("LOG_LEVEL", default="INFO")

# Timezone configuration
TIMEZONE = "America/Sao_Paulo"

# Sentry
SENTRY_ENABLE = False
SENTRY_DSN = None
SENTRY_ENVIRONMENT = None

# OIDC
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
CACHE_CAR_POSITIONS_TTL = int(getenv_or_action("CACHE_CAR_POSITIONS_TTL", default=60 * 10))
