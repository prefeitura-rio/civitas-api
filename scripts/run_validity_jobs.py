#!/usr/bin/env python3
"""
Atualiza vínculos placa–demandante conforme valid_until (active) e envia avisos Discord.

Uso típico com cron (1x/dia ou mais frequente para expiração precisa):
  poetry run python scripts/run_validity_jobs.py

Variáveis opcionais:
  VALIDITY_JOB_SKIP_LOCK=true — não usa lock Redis (ex.: dev com Redis indisponível)
"""

import asyncio
import os
import sys

import redis
from loguru import logger
from tortoise import Tortoise

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import config  # noqa: E402
from app.db import TORTOISE_ORM  # noqa: E402
from app.services.monitored_plate_validity import (  # noqa: E402
    run_monitored_plate_validity_jobs,
)

LOCK_KEY = "civitas:validity_job_lock"
LOCK_TTL_SEC = 600


def _try_acquire_lock():
    if os.getenv("VALIDITY_JOB_SKIP_LOCK", "").lower() in ("1", "true", "yes"):
        logger.warning("VALIDITY_JOB_SKIP_LOCK set — rodando sem lock distribuído")
        return None
    try:
        r = redis.Redis(
            host=config.REDIS_HOST,
            port=int(config.REDIS_PORT),
            db=int(config.REDIS_DB),
            password=config.REDIS_PASSWORD or None,
            socket_connect_timeout=5,
        )
        if not r.set(LOCK_KEY, b"1", nx=True, ex=LOCK_TTL_SEC):
            logger.info("Outra instância já está rodando o job (lock Redis); saindo.")
            return False
        return r
    except Exception as exc:
        logger.error(
            "Redis lock indisponível: {} — abortando para evitar duplicata.",
            exc,
        )
        raise


def _release_lock(r) -> None:
    if r is None:
        return
    try:
        r.delete(LOCK_KEY)
    except Exception as exc:
        logger.warning("Falha ao liberar lock Redis: {}", exc)


async def _async_main() -> int:
    lock_client = _try_acquire_lock()
    if lock_client is False:
        return 0
    await Tortoise.init(config=TORTOISE_ORM)
    try:
        result = await run_monitored_plate_validity_jobs()
        logger.info("Job concluído: {}", result)
    finally:
        await Tortoise.close_connections()
        _release_lock(lock_client)
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_async_main()))


if __name__ == "__main__":
    main()
