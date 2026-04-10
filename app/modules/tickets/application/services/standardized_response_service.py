# -*- coding: utf-8 -*-
from __future__ import annotations

from fastapi import HTTPException
from tortoise.expressions import Q

from app.modules.tickets.application.dtos import (
    StandardizedResponseCreateIn,
    StandardizedResponseListItemOut,
    StandardizedResponseOut,
    StandardizedResponsePageOut,
    StandardizedResponseUpdateIn,
)
from app.modules.tickets.domain.entities import StandardizedResponse



def _normalize_multiline_text(value: str) -> str:
    lines = value.strip().splitlines()
    return "\n".join(line.rstrip() for line in lines).strip()


def _to_standardized_response_out(
    row: StandardizedResponse,
) -> StandardizedResponseOut:
    return StandardizedResponseOut(
        id=str(row.id),
        created_at=row.created_at,
        category=row.category,
        title=row.title,
        when_to_use=row.when_to_use,
        body=row.body,
        is_active=row.is_active,
    )

async def create_standardized_response(
    *,
    data: StandardizedResponseCreateIn,
) -> StandardizedResponseOut:
    exists = await StandardizedResponse.filter(
        category=data.category.value,
        title__iexact=data.title,
    ).exists()

    if exists:
        raise HTTPException(
            status_code=409,
            detail="Já existe uma resposta padronizada com esse título nesta categoria.",
        )

    row = await StandardizedResponse.create(
        category=data.category.value,
        title=data.title,
        when_to_use=data.when_to_use,
        body=data.body,
        is_active=data.is_active,
    )

    return _to_standardized_response_out(row)


async def list_standardized_responses(
    *,
    search: str | None = None,
    category: str | None = None,
    is_active: bool | None = None,
) -> StandardizedResponsePageOut:
    query = StandardizedResponse.all()

    if search and search.strip():
        term = search.strip()
        query = query.filter(
            Q(title__icontains=term)
            | Q(when_to_use__icontains=term)
            | Q(body__icontains=term)
        )

    if category and category.strip():
        query = query.filter(category=category.strip())

    if is_active is not None:
        query = query.filter(is_active=is_active)

    total = await query.count()
    rows = await query.order_by("category", "title")

    items = [
        StandardizedResponseListItemOut(
            id=str(row.id),
            created_at=row.created_at,
            category=row.category,
            title=row.title,
            when_to_use=row.when_to_use,
            is_active=row.is_active,
        )
        for row in rows
    ]

    return StandardizedResponsePageOut(
        items=items,
        total=total,
    )


async def get_standardized_response_by_id(
    *,
    standardized_response_id: str,
) -> StandardizedResponseOut:
    row = await StandardizedResponse.get_or_none(id=standardized_response_id)
    if not row:
        raise HTTPException(
            status_code=404,
            detail="Resposta padronizada não encontrada.",
        )

    return _to_standardized_response_out(row)


async def update_standardized_response(
    *,
    standardized_response_id: str,
    data: StandardizedResponseUpdateIn,
) -> StandardizedResponseOut:
    row = await StandardizedResponse.get_or_none(id=standardized_response_id)
    if not row:
        raise HTTPException(
            status_code=404,
            detail="Resposta padronizada não encontrada.",
        )

    next_category = row.category
    if data.category is not None:
        next_category = data.category.value

    next_title = row.title
    if data.title is not None:
        next_title = data.title

    if data.category is not None or data.title is not None:
        exists = await StandardizedResponse.filter(
            category=next_category,
            title__iexact=next_title,
        ).exclude(id=row.id).exists()
        if exists:
            raise HTTPException(
                status_code=409,
                detail="Já existe uma resposta padronizada com esse título nesta categoria.",
            )

    if data.category is not None:
        row.category = data.category.value

    if data.title is not None:
        row.title = data.title

    if data.when_to_use is not None:
        row.when_to_use = data.when_to_use if data.when_to_use.strip() else None

    if data.body is not None:
        row.body = data.body

    if data.is_active is not None:
        row.is_active = data.is_active

    await row.save()
    return _to_standardized_response_out(row)


async def delete_standardized_response(
    *,
    standardized_response_id: str,
) -> None:
    row = await StandardizedResponse.get_or_none(id=standardized_response_id)
    if not row:
        raise HTTPException(
            status_code=404,
            detail="Resposta padronizada não encontrada.",
        )

    row.is_active = False
    await row.save()