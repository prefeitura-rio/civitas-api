# -*- coding: utf-8 -*-
"""Envio de e-mail via Gmail API (mesma conta OAuth do sync)."""

from __future__ import annotations

import asyncio
from typing import List
from uuid import UUID

from fastapi import HTTPException, status
from googleapiclient.errors import HttpError
from loguru import logger

from app import config
from app.modules.tickets.application.dtos import EmailSendIn, EmailSendOut
from app.modules.tickets.domain.entities import Email
from app.modules.tickets.infrastructure.gmail_client import get_gmail_client


def _scopes_allow_send() -> bool:
    raw = (config.GMAIL_SCOPES or "").strip()
    parts: List[str] = [s.strip() for s in raw.split(",") if s.strip()]
    for s in parts:
        sl = s.lower().rstrip("/")
        if "gmail.send" in sl:
            return True
        if "gmail.compose" in sl:
            return True
        if "gmail.modify" in sl:
            return True
        if sl.endswith("/auth/gmail") and "readonly" not in sl:
            return True
    return False


def gmail_send_config_ok() -> bool:
    if not (
        config.GMAIL_CLIENT_ID
        and config.GMAIL_CLIENT_SECRET
        and config.GMAIL_REFRESH_TOKEN
    ):
        return False
    return _scopes_allow_send()


def _http_error_detail(exc: HttpError) -> str:
    try:
        content = exc.content.decode("utf-8", errors="replace") if exc.content else ""
        return content or str(exc)
    except Exception:
        return str(exc)


async def send_email(payload: EmailSendIn) -> EmailSendOut:
    if not gmail_send_config_ok():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Envio de e-mail indisponível: credenciais Gmail incompletas ou "
                "GMAIL_SCOPES sem permissão de envio (ex.: incluir "
                "https://www.googleapis.com/auth/gmail.send e renovar o refresh token)."
            ),
        )

    thread_id = payload.thread_id
    reply_to_gmail_message_id: str | None = None

    if payload.reply_to_email_id is not None:
        email = await Email.get_or_none(id=payload.reply_to_email_id)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email de referência não encontrado.",
            )
        if not thread_id and email.thread_id:
            thread_id = email.thread_id
        reply_to_gmail_message_id = email.message_id

    client = get_gmail_client()

    def _send() -> dict:
        return client.send_message(
            to_addresses=[str(t) for t in payload.to],
            subject=payload.subject,
            body_text=payload.body_text,
            body_html=payload.body_html,
            thread_id=thread_id,
            reply_to_gmail_message_id=reply_to_gmail_message_id,
        )

    try:
        sent = await asyncio.to_thread(_send)
    except HttpError as e:
        logger.error(f"Gmail API ao enviar: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Falha ao enviar pelo Gmail: {_http_error_detail(e)}",
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.exception(f"Erro inesperado ao enviar e-mail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao enviar e-mail.",
        ) from e

    mid = sent.get("id")
    if not mid:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Resposta do Gmail sem id da mensagem.",
        )

    return EmailSendOut(
        gmail_message_id=str(mid),
        thread_id=sent.get("threadId"),
    )
