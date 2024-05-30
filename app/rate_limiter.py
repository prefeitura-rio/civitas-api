# -*- coding: utf-8 -*-
from slowapi import Limiter
from slowapi.util import get_remote_address

from app import config

redis_url = (
    f"redis://default:{config.REDIS_PASSWORD}@{config.REDIS_HOST}:{config.REDIS_PORT}/{config.REDIS_DB}"  # noqa
    if config.REDIS_PASSWORD
    else f"redis://{config.REDIS_HOST}:{config.REDIS_PORT}/{config.REDIS_DB}"
)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[config.RATE_LIMIT_DEFAULT],
    storage_uri=redis_url,  # noqa
)
