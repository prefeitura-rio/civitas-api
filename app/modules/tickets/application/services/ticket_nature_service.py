# -*- coding: utf-8 -*-
from __future__ import annotations

from fastapi import HTTPException
from tortoise.expressions import Q

from app.modules.tickets.application.dtos import (
    TicketCatalogCreateIn,
    TicketCatalogUpdateIn,
    TicketNatureListItemOut,
    TicketNatureOut,
    TicketNaturePageOut,
)
from app.modules.tickets.domain.entities import TicketNature


def _normalize_name(name: str) -> str:
    return " ".join(name.strip().split())


def _to_ticket_nature_out(row: TicketNature) -> TicketNatureOut:
    return TicketNatureOut(
        id=str(row.id),
        created_at=row.created_at,
        name=row.name,
        description=row.description,
        is_active=row.is_active,
    )


async def create_ticket_nature(*, data: TicketCatalogCreateIn) -> TicketNatureOut:
    normalized_name = _normalize_name(data.name)

    exists = await TicketNature.filter(name__iexact=normalized_name).exists()
    if exists:
        raise HTTPException(
            status_code=409,
            detail="Já existe uma natureza com esse nome.",
        )

    row = await TicketNature.create(
        name=normalized_name,
        description=data.description,
        is_active=data.is_active,
    )

    return _to_ticket_nature_out(row)


async def list_ticket_natures(
    *,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    is_active: bool | None = None,
) -> TicketNaturePageOut:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    offset = (page - 1) * page_size

    query = TicketNature.all()

    if search and search.strip():
        termo = search.strip()
        query = query.filter(
            Q(name__icontains=termo) | Q(description__icontains=termo)
        )

    if is_active is not None:
        query = query.filter(is_active=is_active)

    total = await query.count()
    rows = await query.order_by("name").offset(offset).limit(page_size)

    items = [
        TicketNatureListItemOut(
            id=str(row.id),
            created_at=row.created_at,
            name=row.name,
            is_active=row.is_active,
        )
        for row in rows
    ]

    return TicketNaturePageOut(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
    )


async def get_ticket_nature_by_id(*, nature_id: str) -> TicketNatureOut:
    row = await TicketNature.get_or_none(id=nature_id)
    if not row:
        raise HTTPException(status_code=404, detail="Natureza não encontrada.")

    return _to_ticket_nature_out(row)


async def update_ticket_nature(
    *,
    nature_id: str,
    data: TicketCatalogUpdateIn,
) -> TicketNatureOut:
    row = await TicketNature.get_or_none(id=nature_id)
    if not row:
        raise HTTPException(status_code=404, detail="Natureza não encontrada.")

    if data.name is not None:
        normalized_name = _normalize_name(data.name)

        exists = await TicketNature.filter(name__iexact=normalized_name).exclude(
            id=row.id
        ).exists()
        if exists:
            raise HTTPException(
                status_code=409,
                detail="Já existe uma natureza com esse nome.",
            )

        row.name = normalized_name

    if data.description is not None:
        row.description = data.description

    if data.is_active is not None:
        row.is_active = data.is_active

    await row.save()
    return _to_ticket_nature_out(row)


async def delete_ticket_nature(*, nature_id: str) -> None:
    row = await TicketNature.get_or_none(id=nature_id)
    if not row:
        raise HTTPException(status_code=404, detail="Natureza não encontrada.")

    has_tickets = await row.tickets.all().exists()
    if has_tickets:
        raise HTTPException(
            status_code=409,
            detail="Não é possível excluir a natureza porque ela está vinculada a tickets.",
        )

    await row.delete()