# -*- coding: utf-8 -*-
from __future__ import annotations

import uuid

from fastapi import HTTPException
from tortoise.expressions import Q

from app.modules.tickets.application.dtos import (
    EmailTemplateCreateIn,
    EmailTemplateListItemOut,
    EmailTemplateOut,
    EmailTemplatePageOut,
    EmailTemplateUpdateIn,
)
from app.modules.tickets.domain.entities import EmailTemplate


def _to_out(row: EmailTemplate) -> EmailTemplateOut:
    return EmailTemplateOut(
        id=str(row.id),
        created_at=row.created_at,
        updated_at=row.updated_at,
        title=row.title,
        body_html=row.body_html,
        is_active=row.is_active,
    )


def _to_list_item(row: EmailTemplate) -> EmailTemplateListItemOut:
    return EmailTemplateListItemOut(
        id=str(row.id),
        created_at=row.created_at,
        updated_at=row.updated_at,
        title=row.title,
        is_active=row.is_active,
    )


async def create_email_template(*, data: EmailTemplateCreateIn) -> EmailTemplateOut:
    exists = await EmailTemplate.filter(title__iexact=data.title).exists()
    if exists:
        raise HTTPException(
            status_code=409,
            detail="Já existe um template de email com esse título.",
        )

    row = await EmailTemplate.create(
        id=uuid.uuid4(),
        title=data.title,
        body_html=data.body_html,
        is_active=data.is_active,
    )
    return _to_out(row)


async def list_email_templates(
    *,
    search: str | None = None,
    is_active: bool | None = None,
) -> EmailTemplatePageOut:
    query = EmailTemplate.all()

    if search and search.strip():
        termo = search.strip()
        query = query.filter(Q(title__icontains=termo))

    if is_active is not None:
        query = query.filter(is_active=is_active)

    total = await query.count()
    rows = await query.order_by("-updated_at")

    items = [_to_list_item(row) for row in rows]
    return EmailTemplatePageOut(items=items, total=total)


async def get_email_template_by_id(*, template_id: str) -> EmailTemplateOut:
    row = await EmailTemplate.get_or_none(id=template_id)
    if not row:
        raise HTTPException(status_code=404, detail="Template de email não encontrado.")
    return _to_out(row)


async def update_email_template(
    *,
    template_id: str,
    data: EmailTemplateUpdateIn,
) -> EmailTemplateOut:
    row = await EmailTemplate.get_or_none(id=template_id)
    if not row:
        raise HTTPException(status_code=404, detail="Template de email não encontrado.")

    if data.title is not None:
        conflict = (
            await EmailTemplate.filter(title__iexact=data.title)
            .exclude(id=template_id)
            .exists()
        )
        if conflict:
            raise HTTPException(
                status_code=409,
                detail="Já existe um template de email com esse título.",
            )
        row.title = data.title

    if data.body_html is not None:
        row.body_html = data.body_html

    if data.is_active is not None:
        row.is_active = data.is_active

    await row.save()
    return _to_out(row)


async def delete_email_template(*, template_id: str) -> None:
    row = await EmailTemplate.get_or_none(id=template_id)
    if not row:
        raise HTTPException(status_code=404, detail="Template de email não encontrado.")
    row.is_active = False
    await row.save()
