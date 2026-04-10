# -*- coding: utf-8 -*-
"""Cliente síncrono Gmail API (usar via asyncio.to_thread no app async)."""

from __future__ import annotations

import base64
import html as html_module
import re
from dataclasses import dataclass
from datetime import datetime
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional, Tuple

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from loguru import logger

from app import config


def build_inbox_search_query(
    after_internal_date_ms: Optional[int],
    initial_newer_than_days: int,
) -> str:
    """
    Critério de busca na INBOX para users.messages.list (paginado depois).
    - Sem marca anterior: janela relativa (primeira carga).
    - Com marca: mensagens com internalDate após o watermark (incremental).
    """
    if after_internal_date_ms is None:
        return f"newer_than:{initial_newer_than_days}d"
    after_sec = (after_internal_date_ms + 1) // 1000
    return f"after:{after_sec}"


@dataclass
class GmailEmailPayload:
    message_id: str
    thread_id: Optional[str]
    from_address: Optional[str]
    from_name: Optional[str]
    to_address: Optional[str]
    subject: Optional[str]
    snippet: str
    body_preview: Optional[str]
    date: Optional[datetime]
    internal_date: int
    has_attachments: bool
    is_read: bool
    label_ids: str


class GmailClient:
    """Interação com Gmail API (OAuth2 refresh token)."""

    def _scopes(self) -> List[str]:
        raw = (config.GMAIL_SCOPES or "").strip()
        return [s.strip() for s in raw.split(",") if s.strip()]

    def _credentials(self) -> Credentials:
        creds = Credentials(
            token=None,
            refresh_token=config.GMAIL_REFRESH_TOKEN,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=config.GMAIL_CLIENT_ID,
            client_secret=config.GMAIL_CLIENT_SECRET,
            scopes=self._scopes(),
        )
        creds.refresh(Request())
        return creds

    def _get_service(self):
        creds = self._credentials()
        return build("gmail", "v1", credentials=creds, cache_discovery=False)

    def _parse_email_headers(self, headers: List[Dict[str, Any]]) -> Dict[str, str]:
        result: Dict[str, str] = {}
        header_map = {"From": "from", "To": "to", "Subject": "subject", "Date": "date"}
        for header in headers:
            name = header.get("name", "")
            if name in header_map:
                result[header_map[name]] = header.get("value", "")
            elif name.lower() == "message-id":
                result["message_id"] = header.get("value", "")
        return result

    def _extract_sender_info(self, from_header: str) -> tuple[Optional[str], Optional[str]]:
        if not from_header:
            return None, None
        if "<" in from_header and ">" in from_header:
            name = from_header.split("<")[0].strip().strip('"')
            email_addr = from_header.split("<")[1].split(">")[0].strip()
            return name or email_addr, email_addr
        return from_header, from_header

    def _check_attachments(self, payload: Dict[str, Any]) -> bool:
        parts = payload.get("parts", [])
        for part in parts:
            if part.get("filename"):
                return True
            if part.get("parts") and self._check_attachments(part):
                return True
        return False

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            return parsedate_to_datetime(date_str)
        except Exception as e:
            logger.warning(f"Falha ao parsear data '{date_str}': {e}")
            return None

    def _decode_body_data(self, data_b64: str) -> str:
        if not data_b64:
            return ""
        pad = "=" * (-len(data_b64) % 4)
        raw = base64.urlsafe_b64decode(data_b64 + pad)
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("latin-1", errors="replace")

    def _html_to_text(self, html: str) -> str:
        if not html:
            return ""
        cleaned = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
        cleaned = re.sub(r"<[^>]+>", " ", cleaned)
        text = html_module.unescape(cleaned)
        return re.sub(r"\s+", " ", text).strip()

    def _read_part_body(
        self,
        service: Any,
        message_id: str,
        part: Dict[str, Any],
    ) -> Optional[str]:
        body = part.get("body") or {}
        data = body.get("data")
        if data:
            return self._decode_body_data(data)
        att_id = body.get("attachmentId")
        mime = part.get("mimeType", "")
        if not att_id or mime not in ("text/plain", "text/html"):
            return None
        try:
            att = (
                service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=message_id, id=att_id)
                .execute()
            )
            raw = att.get("data", "")
            return self._decode_body_data(raw) if raw else None
        except Exception as e:
            logger.warning(f"Corpo em attachmentId não obtido ({message_id}): {e}")
            return None

    def _collect_body_parts(
        self,
        service: Any,
        message_id: str,
        part: Dict[str, Any],
        plain_chunks: List[str],
        html_chunks: List[str],
    ) -> None:
        mime = part.get("mimeType", "")
        nested = part.get("parts") or []
        if mime.startswith("multipart/"):
            for p in nested:
                self._collect_body_parts(service, message_id, p, plain_chunks, html_chunks)
            return
        text = self._read_part_body(service, message_id, part)
        if not text:
            return
        if mime == "text/plain":
            plain_chunks.append(text)
        elif mime == "text/html":
            html_chunks.append(text)

    def _extract_body_preview(
        self,
        service: Any,
        message_id: str,
        payload: Dict[str, Any],
        max_chars: int = 2_000_000,
    ) -> Optional[str]:
        """Texto completo do corpo (plain preferido; HTML vira texto). Gmail `snippet` é curto por definição."""
        plain_chunks: List[str] = []
        html_chunks: List[str] = []
        self._collect_body_parts(service, message_id, payload, plain_chunks, html_chunks)
        body: Optional[str] = None
        if plain_chunks:
            body = "\n".join(s.strip() for s in plain_chunks if s.strip()).strip()
        elif html_chunks:
            combined = "\n".join(html_chunks)
            body = self._html_to_text(combined)
        if body and len(body) > max_chars:
            body = body[:max_chars]
        return body or None

    def _list_all_inbox_message_ids(
        self,
        service: Any,
        query: str,
        list_page_size: int,
    ) -> List[str]:
        """Pagina users.messages.list até não haver nextPageToken."""
        page_size = max(1, min(list_page_size, 500))
        collected: List[str] = []
        page_token: Optional[str] = None
        pages = 0
        while True:
            kwargs: Dict[str, Any] = {
                "userId": "me",
                "maxResults": page_size,
                "labelIds": ["INBOX"],
            }
            if query:
                kwargs["q"] = query
            if page_token:
                kwargs["pageToken"] = page_token

            results = service.users().messages().list(**kwargs).execute()
            pages += 1
            batch = results.get("messages") or []
            for m in batch:
                collected.append(m["id"])

            page_token = results.get("nextPageToken")
            if not page_token:
                break

        logger.info(
            f"Gmail: list INBOX paginado — {len(collected)} id(s) em {pages} página(s), "
            f"maxResults={page_size}, q={query!r}."
        )
        return collected

    def fetch_inbox_emails_paginated(
        self,
        query: str,
        list_page_size: int,
    ) -> List[GmailEmailPayload]:
        """
        Lista todas as mensagens que batem com `q` na INBOX (paginação completa)
        e carrega o corpo de cada uma.
        """
        try:
            service = self._get_service()
            message_ids = self._list_all_inbox_message_ids(service, query, list_page_size)

            emails: List[GmailEmailPayload] = []
            for msg_id in message_ids:
                try:
                    detail = self._fetch_email_detail(service, msg_id)
                    if detail:
                        emails.append(detail)
                except Exception as e:
                    logger.error(f"Erro ao buscar email {msg_id}: {e}")
                    continue

            return emails

        except HttpError as e:
            logger.error(f"Erro HTTP Gmail API: {e}")
            raise
        except Exception as e:
            logger.error(f"Erro ao buscar emails: {e}")
            raise

    def _fetch_email_detail(self, service, message_id: str) -> Optional[GmailEmailPayload]:
        try:
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )
            payload = msg.get("payload", {})
            headers = self._parse_email_headers(payload.get("headers", []))
            from_name, from_address = self._extract_sender_info(headers.get("from", ""))
            date = self._parse_date(headers.get("date", ""))
            has_attachments = self._check_attachments(payload)
            label_ids = msg.get("labelIds", [])
            is_read = "UNREAD" not in label_ids
            body_preview = self._extract_body_preview(service, msg["id"], payload)

            return GmailEmailPayload(
                message_id=msg["id"],
                thread_id=msg.get("threadId"),
                from_address=from_address,
                from_name=from_name,
                to_address=headers.get("to"),
                subject=headers.get("subject", "(Sem assunto)"),
                snippet=msg.get("snippet", ""),
                body_preview=body_preview,
                date=date,
                internal_date=int(msg.get("internalDate", 0)),
                has_attachments=has_attachments,
                is_read=is_read,
                label_ids=",".join(label_ids),
            )
        except Exception as e:
            logger.error(f"Erro ao buscar detalhe do email {message_id}: {e}")
            return None

    def _find_pdf_parts(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        pdf_parts: List[Dict[str, Any]] = []
        parts = payload.get("parts", [])
        for part in parts:
            mime_type = part.get("mimeType", "")
            filename = part.get("filename", "")
            if filename and mime_type == "application/pdf":
                body = part.get("body", {})
                pdf_parts.append(
                    {
                        "attachment_id": body.get("attachmentId"),
                        "filename": filename,
                        "mime_type": mime_type,
                        "size": body.get("size", 0),
                    }
                )
            if part.get("parts"):
                pdf_parts.extend(self._find_pdf_parts(part))
        return pdf_parts

    def download_pdf_attachments(self, message_id: str) -> List[Dict[str, Any]]:
        """
        Baixa PDFs do Gmail e retorna metadados + bytes (sem gravar em disco local).
        """
        try:
            service = self._get_service()
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )
            payload = msg.get("payload", {})
            pdf_parts = self._find_pdf_parts(payload)
            if not pdf_parts:
                logger.info(f"Nenhum PDF em anexo para a mensagem {message_id}")
                return []

            downloaded: List[Dict[str, Any]] = []
            for part_info in pdf_parts:
                att_id = part_info["attachment_id"]
                filename = part_info["filename"]
                if not att_id:
                    logger.warning(f"Sem attachmentId para {filename} em {message_id}")
                    continue
                try:
                    att = (
                        service.users()
                        .messages()
                        .attachments()
                        .get(userId="me", messageId=message_id, id=att_id)
                        .execute()
                    )
                    data = att.get("data", "")
                    file_bytes = base64.urlsafe_b64decode(data)
                    safe_filename = "".join(
                        c for c in filename if c.isalnum() or c in "._- "
                    ).strip()
                    if not safe_filename.lower().endswith(".pdf"):
                        safe_filename += ".pdf"
                    downloaded.append(
                        {
                            "attachment_id": att_id,
                            "filename": safe_filename,
                            "mime_type": part_info["mime_type"],
                            "size": len(file_bytes),
                            "content_bytes": file_bytes,
                        }
                    )
                    logger.info(
                        f"PDF baixado: {safe_filename} ({len(file_bytes)} bytes) msg={message_id}"
                    )
                except Exception as e:
                    logger.error(f"Erro ao baixar anexo {filename} em {message_id}: {e}")
                    continue

            return downloaded

        except Exception as e:
            logger.error(f"Erro ao baixar anexos para {message_id}: {e}")
            return []

    def _get_reply_rfc_message_id_and_subject(
        self,
        service: Any,
        gmail_message_id: str,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Message-ID RFC e assunto da mensagem original (resposta em thread)."""
        try:
            msg = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=gmail_message_id,
                    format="metadata",
                    metadataHeaders=["Message-ID", "Subject"],
                )
                .execute()
            )
            payload = msg.get("payload", {}) or {}
            headers = self._parse_email_headers(payload.get("headers", []))
            return headers.get("message_id"), headers.get("subject")
        except Exception as e:
            logger.warning(f"Metadados de reply não obtidos ({gmail_message_id}): {e}")
            return None, None

    def _build_mime_message(
        self,
        *,
        to_addresses: List[str],
        subject: str,
        body_text: Optional[str],
        body_html: Optional[str],
        in_reply_to_rfc_message_id: Optional[str],
        references: Optional[str],
    ) -> MIMEMultipart | MIMEText:
        to_addresses = [t.strip() for t in to_addresses if t and str(t).strip()]
        if not to_addresses:
            raise ValueError("Lista de destinatários vazia.")

        if body_html and (body_text or "").strip():
            root: MIMEMultipart | MIMEText = MIMEMultipart("alternative")
            root.attach(MIMEText(body_text or "", "plain", "utf-8"))
            root.attach(MIMEText(body_html, "html", "utf-8"))
        elif body_html:
            root = MIMEText(body_html, "html", "utf-8")
        else:
            root = MIMEText(body_text or "", "plain", "utf-8")

        root["To"] = ", ".join(to_addresses)
        root["Subject"] = subject
        if in_reply_to_rfc_message_id:
            root["In-Reply-To"] = in_reply_to_rfc_message_id.strip()
        if references:
            root["References"] = references.strip()

        return root

    def _build_mime_message_with_inline_images(
        self,
        *,
        to_addresses: List[str],
        subject: str,
        body_text: Optional[str],
        body_html: str,
        in_reply_to_rfc_message_id: Optional[str],
        references: Optional[str],
        inline_images: List[Tuple[str, str, bytes]],
    ) -> MIMEMultipart:
        """
        multipart/related: HTML + partes inline (Content-ID) para cid: no HTML.
        `inline_images`: lista de (cid_sem_aspas, mime principal/subtipo, bytes).
        """
        to_addresses = [t.strip() for t in to_addresses if t and str(t).strip()]
        if not to_addresses:
            raise ValueError("Lista de destinatários vazia.")

        root = MIMEMultipart("related")

        alt = MIMEMultipart("alternative")
        plain = (body_text or "").strip()
        alt.attach(MIMEText(plain, "plain", "utf-8"))
        alt.attach(MIMEText(body_html, "html", "utf-8"))
        root.attach(alt)

        for cid, mime, raw in inline_images:
            if "/" not in mime:
                mime = "application/octet-stream"
            main, sub = mime.split("/", 1)
            if main == "image":
                part = MIMEImage(raw, _subtype=sub)
            else:
                raise ValueError(f"Tipo MIME não suportado para inline: {mime}")
            part.add_header("Content-ID", f"<{cid}>")
            part.add_header("Content-Disposition", "inline", filename=f"inline.{sub}")
            root.attach(part)

        root["To"] = ", ".join(to_addresses)
        root["Subject"] = subject
        if in_reply_to_rfc_message_id:
            root["In-Reply-To"] = in_reply_to_rfc_message_id.strip()
        if references:
            root["References"] = references.strip()

        return root

    def send_message(
        self,
        *,
        to_addresses: List[str],
        subject: str,
        body_text: Optional[str] = None,
        body_html: Optional[str] = None,
        thread_id: Optional[str] = None,
        reply_to_gmail_message_id: Optional[str] = None,
        inline_cid_images: Optional[List[Tuple[str, str, bytes]]] = None,
    ) -> Dict[str, Any]:
        """
        Envia e-mail via `users.messages.send` (mesma conta OAuth).
        Com `reply_to_gmail_message_id`, preenche In-Reply-To/References.
        Com `thread_id`, a mensagem entra na mesma conversa no Gmail.
        """
        try:
            service = self._get_service()
            in_reply_to: Optional[str] = None
            references: Optional[str] = None

            if reply_to_gmail_message_id:
                rfc_mid, _orig_subj = self._get_reply_rfc_message_id_and_subject(
                    service, reply_to_gmail_message_id
                )
                if rfc_mid:
                    in_reply_to = rfc_mid
                    references = rfc_mid

            html = (body_html or "").strip()
            if inline_cid_images and html:
                mime = self._build_mime_message_with_inline_images(
                    to_addresses=to_addresses,
                    subject=subject,
                    body_text=body_text,
                    body_html=body_html or "",
                    in_reply_to_rfc_message_id=in_reply_to,
                    references=references,
                    inline_images=inline_cid_images,
                )
            else:
                mime = self._build_mime_message(
                    to_addresses=to_addresses,
                    subject=subject,
                    body_text=body_text,
                    body_html=body_html,
                    in_reply_to_rfc_message_id=in_reply_to,
                    references=references,
                )
            raw_b64 = base64.urlsafe_b64encode(mime.as_bytes()).decode("utf-8")
            send_body: Dict[str, Any] = {"raw": raw_b64}
            if thread_id:
                send_body["threadId"] = thread_id

            sent = (
                service.users().messages().send(userId="me", body=send_body).execute()
            )
            logger.info(
                f"Gmail: mensagem enviada id={sent.get('id')} threadId={sent.get('threadId')}"
            )
            return sent

        except HttpError as e:
            logger.error(f"Erro HTTP Gmail API ao enviar: {e}")
            raise
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem Gmail: {e}")
            raise


_gmail_client: GmailClient | None = None


def get_gmail_client() -> GmailClient:
    global _gmail_client
    if _gmail_client is None:
        _gmail_client = GmailClient()
    return _gmail_client
