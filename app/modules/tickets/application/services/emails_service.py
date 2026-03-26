from app.modules.tickets.application.dtos import AttachmentOut, EmailBase, EmailOut, EmailPageOut
from app.modules.tickets.domain.entities import Email
from fastapi import HTTPException




async def list_emails(
    *,
    page: int = 1,
    page_size: int = 10,
) -> EmailPageOut:
    if page < 1:
        raise HTTPException(status_code=400, detail="Página inválida.")

    if page_size < 1 or page_size > 100:
        raise HTTPException(
            status_code=400,
            detail="page_size deve estar entre 1 e 100.",
        )

    query = Email.all()

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
            is_read=email.is_read,
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
        is_read=email.is_read,
        label_ids=email.label_ids,
        created_at=email.created_at,
        updated_at=email.updated_at,
        attachments=[
            AttachmentOut(
                id=att.id,
                filename=att.filename,
                mime_type=att.mime_type,
                size=att.size,
                file_path=att.file_path,
            )
            for att in email.attachments
        ],
    )