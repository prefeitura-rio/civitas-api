# -*- coding: utf-8 -*-
"""Tarefa em background para sincronização periódica Gmail → banco."""

from __future__ import annotations

import asyncio
from typing import Optional

from loguru import logger

from app import config
from app.modules.tickets.application.services.email_sync_service import (
    gmail_sync_config_ok,
    run_email_sync_loop,
)

_email_sync_task: Optional[asyncio.Task] = None


async def start_email_sync_background() -> None:
    """Inicia o loop asyncio no mesmo event loop da aplicação (compatível com Tortoise)."""
    global _email_sync_task

    if not config.ENABLE_EMAIL_SYNC:
        return

    if not gmail_sync_config_ok():
        logger.warning(
            "ENABLE_EMAIL_SYNC está ativo mas as credenciais Gmail (GMAIL_CLIENT_ID, "
            "GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN) estão incompletas; sync não será iniciado."
        )
        return

    if _email_sync_task and not _email_sync_task.done():
        return

    _email_sync_task = asyncio.create_task(
        run_email_sync_loop(),
        name="email_sync_loop",
    )
    logger.info(
        f"Sync de emails em background iniciado (intervalo: "
        f"{config.EMAIL_POLLING_INTERVAL_SECONDS}s)."
    )


async def stop_email_sync_background() -> None:
    global _email_sync_task
    if _email_sync_task and not _email_sync_task.done():
        _email_sync_task.cancel()
        try:
            await _email_sync_task
        except asyncio.CancelledError:
            pass
    _email_sync_task = None
    logger.info("Sync de emails em background encerrado.")
