import uuid

from app.modules.tickets.domain.enum import EmailStatus
from starlette.responses import Response

from app.modules.tickets.application.dtos import EmailAttachmentOut, EmailBase, EmailOut, EmailPageOut
from app.modules.tickets.domain.entities import EmailAttachment, Email
from app.modules.tickets.infrastructure.gcs_upload import build_email_attachment_object_name, gcs_delete_object, gcs_download_file_bytes, gcs_upload_file_bytes
from fastapi import HTTPException
from app.config import GCS_BUCKET_NAME
from tortoise.transactions import in_transaction
from fastapi import UploadFile
from uuid import UUID


async def list_emails(
    *,
    page: int = 1,
    page_size: int = 10,
    statuses: list[EmailStatus] | None = None,
) -> EmailPageOut:
    if page < 1:
        raise HTTPException(status_code=400, detail="Página inválida.")

    if page_size < 1 or page_size > 100:
        raise HTTPException(
            status_code=400,
            detail="page_size deve estar entre 1 e 100.",
        )

    query = Email.all()

    if statuses:
        query = query.filter(status__in=statuses)

    total = await query.count()

    offset = (page - 1) * page_size
    emails = (
        await query
        .order_by("-date", "-created_at")
        .offset(offset)
        .limit(page_size)
    )

    if not emails:
        return EmailPageOut(items=[], total=total)

    items = [
        EmailBase(
            id=str(email.id),
            message_id=email.message_id,
            thread_id=email.thread_id,
            from_address=email.from_address,
            from_name=email.from_name,
            to_address=email.to_address,
            subject=email.subject,
            snippet=email.snippet,
            date=email.date,
            internal_date=email.internal_date,
            has_attachments=email.has_attachments,
        )
        for email in emails
    ]

    return EmailPageOut(items=items, total=total)

async def get_email_by_id(email_id: str) -> EmailOut:

    email = await Email.get_or_none(id=email_id).prefetch_related(
            "attachments")
        
    if not email:
        raise HTTPException(status_code=404, detail="Email não encontrado")

    return EmailOut(
        id=str(email.id),
        message_id=email.message_id,
        thread_id=email.thread_id,
        from_address=email.from_address,
        from_name=email.from_name,
        to_address=email.to_address,
        subject=email.subject,
        snippet=email.snippet,
        body_preview=email.body_preview,
        date=email.date,
        internal_date=email.internal_date,
        has_attachments=email.has_attachments,
        status=email.status,
        label_ids=email.label_ids,
        created_at=email.created_at,
        updated_at=email.updated_at,
        attachments=[
            EmailAttachmentOut(
                id=att.id,
                filename=att.filename,
                mime_type=att.mime_type,
                size=att.size,
                file_path=att.file_path,
            )
            for att in email.attachments
        ],
    )


async def mark_email_as_spam(*, email_id: UUID) -> EmailOut:
    email = await Email.get_or_none(id=email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email não encontrado.")
    email.status = EmailStatus.SPAM
    await email.save(update_fields=["status","updated_at"])
    return await get_email_by_id(email_id)


MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/jpeg",
    "image/png",
}


async def upload_email_attachment(
    *,
    email_id: UUID,
    file: UploadFile,
) -> EmailAttachmentOut:
    email = await Email.get_or_none(id=email_id)

    if not email:
        raise HTTPException(status_code=404, detail="Email não encontrado.")

    if not file:
        raise HTTPException(status_code=400, detail="Arquivo não enviado.")

    filename = (file.filename or "").strip()
    if not filename:
        raise HTTPException(status_code=400, detail="Nome do arquivo inválido.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")

    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"O arquivo excede o limite de {MAX_FILE_BYTES // (1024 * 1024)}MB.",
        )

    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Tipo de arquivo não permitido.",
        )

    object_name = build_email_attachment_object_name(
        str(email.id),
        filename,
    )

    upload_meta = await gcs_upload_file_bytes(
        bucket_name=GCS_BUCKET_NAME,
        object_name=object_name,
        content=content,
        content_type=content_type,
    )

    try:
        async with in_transaction() as connection:
            attachment = await EmailAttachment.create(
                email=email,
                attachment_id=uuid.uuid4(),
                filename=filename,
                mime_type=content_type,
                size=int(upload_meta.get("size") or len(content)),
                file_path=object_name,
                using_db=connection,
            )

            if not email.has_attachments:
                email.has_attachments = True
                await email.save(using_db=connection, update_fields=["has_attachments"])

        return EmailAttachmentOut(
            id=attachment.id,
            filename=attachment.filename,
            mime_type=attachment.mime_type,
            size=attachment.size,
            file_path=attachment.file_path,
        )

    except Exception:
        await gcs_delete_object(
            bucket_name=GCS_BUCKET_NAME,
            object_name=object_name,
        )
        raise


async def download_email_attachment(
    *,
    email_id: UUID,
    attachment_id: int,
) -> Response:
    email = await Email.get_or_none(id=email_id)

    if not email:
        raise HTTPException(status_code=404, detail="Email não encontrado.")

    attachment = await EmailAttachment.get_or_none(
        id=attachment_id,
        email_id=email.id,
    )

    if not attachment:
        raise HTTPException(status_code=404, detail="Anexo não encontrado.")

    content = await gcs_download_file_bytes(
        bucket_name=GCS_BUCKET_NAME,
        object_name=attachment.file_path,
    )

    headers = {
        "Content-Disposition": f'inline; filename="{attachment.filename}"'
    }

    return Response(
        content=content,
        media_type=attachment.mime_type or "application/octet-stream",
        headers=headers,
    )