# -*- coding: utf-8 -*-
"""Envio de resposta padronizada renderizada com o primeiro template HTML ativo."""

from __future__ import annotations

import asyncio
import html as html_module
import mimetypes
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
from googleapiclient.errors import HttpError
from loguru import logger

from app import config
from app.modules.tickets.application.dtos import EmailSendOut

from app.modules.tickets.domain.entities import Email, EmailTemplate
from app.modules.tickets.domain.enum import EmailStatus
from app.modules.tickets.infrastructure.gmail_client import get_gmail_client

DEFAULT_SIGNATURE_NAME = "Equipe CIVITAS"
DEFAULT_SIGNATURE_ROLE = "Sistema de Atendimento Institucional"
DEFAULT_SIGNATURE_ORG = "CIVITAS"


def gmail_send_config_ok() -> bool:
    return bool(
        config.GMAIL_CLIENT_ID
        and config.GMAIL_CLIENT_SECRET
        and config.GMAIL_REFRESH_TOKEN
    )


def _http_error_detail(exc: HttpError) -> str:
    try:
        content = exc.content.decode("utf-8", errors="replace") if exc.content else ""
        return content or str(exc)
    except Exception:
        return str(exc)


def _plain_to_html_fragment(text: str) -> str:
    t = text or ""
    return html_module.escape(t).replace("\n", "<br />\n")


def _reply_subject(original_subject: str | None) -> str:
    s = (original_subject or "").strip() or "(Sem assunto)"
    if s.lower().startswith("re:"):
        return s
    return f"Re: {s}"


def _render_template_html(
    template_body: str,
    *,
    email_title: str,
    email_body_fragment: str,
    signature_name: str,
    signature_role: str,
    signature_org: str,
    email_logo_cid: str,
) -> str:
    return (
        template_body.replace("{{EMAIL_TITLE}}", email_title)
        .replace("{{EMAIL_BODY}}", email_body_fragment)
        .replace("{{SIGNATURE_NAME}}", signature_name)
        .replace("{{SIGNATURE_ROLE}}", signature_role)
        .replace("{{SIGNATURE_ORG}}", signature_org)
        .replace("{{EMAIL_LOGO_CID}}", email_logo_cid)
    )


def _resolve_inline_logo_path() -> Path | None:
    """Arquivo em `EMAIL_TEMPLATE_DEFAULT_INLINE_LOGO` (app/assets/logo_email.png)."""
    default = getattr(config, "EMAIL_TEMPLATE_DEFAULT_INLINE_LOGO", None)
    if default is None:
        return None
    p = Path(default)
    if p.is_file():
        return p
    logger.warning(f"Logo inline não encontrada: {p}")
    return None


def _inline_logo_parts(inline_cid: str) -> list[tuple[str, str, bytes]]:
    p = _resolve_inline_logo_path()
    if p is None:
        return []
    if not p.is_file():
        logger.warning(f"Arquivo de logo inline não encontrado: {p}")
        return []
    mime, _ = mimetypes.guess_type(str(p))
    if not mime or not mime.startswith("image/"):
        mime = "image/png"
    try:
        data = p.read_bytes()
    except OSError as e:
        logger.error(f"Leitura da logo inline falhou: {e}")
        return []
    return [(inline_cid, mime, data)]


async def send_standardized_templated_email(
    *,
    email_id: UUID,
    title: str,
    body: str,
) -> EmailSendOut:
    if not gmail_send_config_ok():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Envio de e-mail indisponível: credenciais Gmail incompletas "
                "(GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN)."
            ),
        )

    template = (
        await EmailTemplate.filter(is_active=True)
        .order_by("created_at")
        .first()
    )
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhum template de e-mail ativo cadastrado.",
        )

    email = await Email.get_or_none(id=email_id)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="E-mail de referência não encontrado.",
        )

    to_addr = (email.from_address or "").strip()
    if not to_addr:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O e-mail de referência não possui from_address para resposta.",
        )

    title_esc = html_module.escape(title.strip())
    body_frag = _plain_to_html_fragment(body)
    sig_name = html_module.escape(DEFAULT_SIGNATURE_NAME)
    sig_role = html_module.escape(DEFAULT_SIGNATURE_ROLE)
    sig_org = html_module.escape(DEFAULT_SIGNATURE_ORG)
    cid_token = config.EMAIL_INLINE_LOGO_CID

    html_out = _render_template_html(
        template.body_html,
        email_title=title_esc,
        email_body_fragment=body_frag,
        signature_name=sig_name,
        signature_role=sig_role,
        signature_org=sig_org,
        email_logo_cid=cid_token,
    )

    subject = _reply_subject(email.subject)
    body_text_plain = body
    inline = _inline_logo_parts(cid_token)

    thread_id = email.thread_id
    reply_gmail_id = email.message_id

    client = get_gmail_client()

    def _send() -> dict:
        return client.send_message(
            to_addresses=[to_addr],
            subject=subject,
            body_text=body_text_plain,
            body_html=html_out,
            thread_id=thread_id,
            reply_to_gmail_message_id=reply_gmail_id,
            inline_cid_images=inline if inline else None,
        )

    try:
        sent = await asyncio.to_thread(_send)
    except HttpError as e:
        logger.error(f"Gmail API ao enviar resposta padronizada: {e}")
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
        logger.exception(f"Erro inesperado ao enviar resposta padronizada: {e}")
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

    try:
        email.status = EmailStatus.RESPONDIDO
        await email.save(update_fields=["status", "updated_at"])
    except Exception as e:
        logger.exception(
            f"E-mail enviado (gmail id={mid}), mas falha ao marcar como Respondido: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "E-mail enviado, mas não foi possível atualizar o status para Respondido. "
                "Tente novamente ou atualize o status manualmente."
            ),
        ) from e

    return EmailSendOut(
        gmail_message_id=str(mid),
        thread_id=sent.get("threadId"),
    )
