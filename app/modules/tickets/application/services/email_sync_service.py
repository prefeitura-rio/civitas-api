# -*- coding: utf-8 -*-
"""Sincronização Gmail → banco (Tortoise) e anexos PDF → GCS."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger
from tortoise.transactions import in_transaction

from app import config
from app.modules.tickets.domain.entities import EmailAttachment, Email
from app.modules.tickets.infrastructure.gcs_upload import (
    build_email_attachment_object_name,
    gcs_upload_file_bytes,
)
from app.modules.tickets.infrastructure.gmail_client import (
    GmailEmailPayload,
    get_gmail_client,
)

_last_sync: Optional[datetime] = None
_emails_synced_total: int = 0
_is_running: bool = False


def gmail_sync_config_ok() -> bool:
    if not config.ENABLE_EMAIL_SYNC:
        return False
    return bool(
        config.GMAIL_CLIENT_ID
        and config.GMAIL_CLIENT_SECRET
        and config.GMAIL_REFRESH_TOKEN
    )


def get_email_sync_status() -> Dict[str, Any]:
    return {
        "last_sync": _last_sync,
        "polling_interval_seconds": config.EMAIL_POLLING_INTERVAL_SECONDS,
        "emails_synced_total": _emails_synced_total,
        "is_running": _is_running,
        "enabled": config.ENABLE_EMAIL_SYNC and gmail_sync_config_ok(),
    }


async def _fetch_emails_thread(
    max_results: int,
    after_timestamp: Optional[int],
) -> List[GmailEmailPayload]:
    client = get_gmail_client()
    return await asyncio.to_thread(client.fetch_emails, max_results, after_timestamp)


async def _download_pdfs_thread(gmail_message_id: str) -> List[Dict[str, Any]]:
    client = get_gmail_client()
    return await asyncio.to_thread(client.download_pdf_attachments, gmail_message_id)


async def _get_latest_internal_date() -> Optional[int]:
    latest = await Email.all().order_by("-internal_date").first()
    return int(latest.internal_date) if latest and latest.internal_date is not None else None


async def _create_email_row(data: GmailEmailPayload) -> Email:
    return await Email.create(
        id=uuid.uuid4(),
        message_id=data.message_id,
        thread_id=data.thread_id,
        from_address=data.from_address,
        from_name=data.from_name,
        to_address=data.to_address,
        subject=data.subject,
        snippet=data.snippet,
        body_preview=None,
        date=data.date,
        internal_date=data.internal_date,
        has_attachments=data.has_attachments,
        is_read=data.is_read,
        label_ids=data.label_ids,
    )


async def _persist_new_emails(
    emails: List[GmailEmailPayload],
) -> List[str]:
    """Insere emails novos. Retorna lista de Gmail message_id criados."""
    created_gmail_ids: List[str] = []
    for data in emails:
        exists = await Email.filter(message_id=data.message_id).exists()
        if exists:
            continue
        try:
            async with in_transaction():
                await _create_email_row(data)
            created_gmail_ids.append(data.message_id)
        except Exception as e:
            logger.error(f"Erro ao criar email {data.message_id}: {e}")
            continue
    if created_gmail_ids:
        logger.info(f"Emails novos persistidos: {len(created_gmail_ids)}")
    return created_gmail_ids


async def _store_pdf_attachments_for_email(
    email_row: Email,
    gmail_message_id: str,
) -> None:
    if await EmailAttachment.filter(email_id=email_row.id).exists():
        return

    pdfs = await _download_pdfs_thread(gmail_message_id)
    if not pdfs:
        return

    for att in pdfs:
        content: bytes = att["content_bytes"]
        filename = att["filename"]
        object_name = build_email_attachment_object_name(str(email_row.id), filename)
        try:
            upload_meta = await gcs_upload_file_bytes(
                bucket_name=config.GCS_BUCKET_NAME,
                object_name=object_name,
                content=content,
                content_type=att.get("mime_type") or "application/pdf",
            )
            async with in_transaction():
                await EmailAttachment.create(
                    email=email_row,
                    attachment_id=str(att["attachment_id"]),
                    filename=filename,
                    mime_type=att.get("mime_type") or "application/pdf",
                    size=int(upload_meta.get("size") or len(content)),
                    file_path=object_name,
                )
            logger.info(
                f"Anexo PDF salvo no GCS: {object_name} (email={email_row.id})"
            )
        except Exception as e:
            logger.error(f"Falha ao gravar anexo {filename} para email {email_row.id}: {e}")


async def run_email_sync_once() -> None:
    """Uma execução completa do sync (cron ou trigger manual)."""
    global _last_sync, _emails_synced_total, _is_running

    if not config.ENABLE_EMAIL_SYNC:
        return
    if not gmail_sync_config_ok():
        return

    if _is_running:
        logger.warning("Sync de emails já em execução, ignorando.")
        return

    _is_running = True
    logger.info("Iniciando sync de emails (Gmail)...")

    try:
        latest = await _get_latest_internal_date()
        after_ts = latest + 1 if latest is not None else None
        logger.info(f"Buscando emails após internal_date (ms): {after_ts}")

        emails = await _fetch_emails_thread(
            max_results=config.EMAIL_SYNC_MAX_RESULTS,
            after_timestamp=after_ts,
        )

        if not emails:
            logger.info("Nenhum email novo encontrado.")
            _last_sync = datetime.now()
            return

        created_ids = await _persist_new_emails(emails)
        _emails_synced_total += len(created_ids)

        for data in emails:
            if data.message_id not in created_ids:
                continue
            if not data.has_attachments:
                continue
            email_row = await Email.get(message_id=data.message_id)
            try:
                await _store_pdf_attachments_for_email(email_row, data.message_id)
            except Exception as e:
                logger.error(
                    f"Erro ao processar anexos para {data.message_id}: {e}"
                )

        _last_sync = datetime.now()
        logger.info(f"Sync de emails concluído. Novos nesta rodada: {len(created_ids)}")
    except Exception as e:
        logger.exception(f"Erro durante sync de emails: {e}")
    finally:
        _is_running = False


async def run_email_sync_loop() -> None:
    """Loop para uso no lifespan (asyncio); primeira execução imediata."""
    while True:
        try:
            await run_email_sync_once()
        except asyncio.CancelledError:
            logger.info("Loop de sync de emails cancelado.")
            raise
        except Exception as e:
            logger.exception(f"Erro no loop de sync de emails: {e}")
        await asyncio.sleep(config.EMAIL_POLLING_INTERVAL_SECONDS)


async def trigger_email_sync_now() -> None:
    """Dispara uma execução (usado pelo endpoint manual)."""
    await run_email_sync_once()
