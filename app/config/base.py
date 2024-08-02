# -*- coding: utf-8 -*-
import traceback
from typing import Dict
from urllib.request import urlopen

import numpy as np
import orjson as json
import pandas as pd
from loguru import logger

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
CACHE_RADAR_POSITIONS_TTL = int(getenv_or_action("CACHE_RADAR_POSITIONS_TTL", default=60 * 60 * 24))
CACHE_WAZE_ALERTS_TTL = int(getenv_or_action("CACHE_WAZE_ALERTS_TTL", default=60 * 5))
CACHE_CAR_BY_RADAR_TTL = int(getenv_or_action("CACHE_CAR_BY_RADAR_TTL", default=60 * 5))
CACHE_CAMERAS_COR_TTL = int(getenv_or_action("CACHE_CAMERAS_COR_TTL", default=60 * 5))

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

# External data that is loaded persistently
DATA_CODCET_TO_CAMERA_NUMERO_CSV_URL = getenv_or_action("DATA_CODCET_TO_CAMERA_NUMERO_CSV_URL")
try:
    _df_codcet_to_camera_numero: pd.DataFrame = pd.read_csv(DATA_CODCET_TO_CAMERA_NUMERO_CSV_URL)
    _df_codcet_to_camera_numero.dropna(inplace=True)
    CODCET_TO_CAMERA_NUMERO: Dict[str, str] = (
        _df_codcet_to_camera_numero.groupby("codcet")["camera_numero"]
        .apply(lambda x: np.random.choice(x))
        .to_dict()
    )
except Exception as exc:
    logger.error(f"Failed to load CODCET to camera_numero mapping: {exc}")
    logger.error(traceback.format_exc())
    CODCET_TO_CAMERA_NUMERO = {}
