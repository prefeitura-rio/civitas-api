# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List

from fastapi import HTTPException
from tortoise.expressions import Q

from app.modules.tickets.application.dtos import (
    TicketCatalogCreateIn,
    TicketCatalogUpdateIn,
    TicketTypeListItemOut,
    TicketTypeOut,
)
from app.modules.tickets.domain.entities import TicketType



def _to_ticket_type_out(row: TicketType) -> TicketTypeOut:
    return TicketTypeOut(
        id=str(row.id),
        created_at=row.created_at,
        name=row.name,
        description=row.description,
        is_active=row.is_active,
    )


async def create_ticket_type(*, data: TicketCatalogCreateIn) -> TicketTypeOut:


    exists = await TicketType.filter(name__iexact=data.name).exists()
    if exists:
        raise HTTPException(
            status_code=409,
            detail="Já existe um tipo de chamado com esse nome.",
        )

    row = await TicketType.create(
        name=data.name,
        description=data.description,
        is_active=data.is_active,
    )

    return _to_ticket_type_out(row)


async def list_ticket_types(
    *,
    search: str | None = None,
    is_active: bool | None = None,
) -> list[TicketTypeListItemOut]:

    query = TicketType.all()

    if search and search.strip():
        termo = search.strip()
        query = query.filter(
            Q(name__icontains=termo) | Q(description__icontains=termo)
        )

    if is_active is not None:
        query = query.filter(is_active=is_active)

    total = await query.count()
    rows = await query.order_by("name")

    items = [
        TicketTypeListItemOut(
            id=str(row.id),
            created_at=row.created_at,
            name=row.name,
            is_active=row.is_active,
        )
        for row in rows
    ]

    return items


async def get_ticket_type_by_id(*, ticket_type_id: str) -> TicketTypeOut:
    row = await TicketType.get_or_none(id=ticket_type_id)
    if not row:
        raise HTTPException(status_code=404, detail="Tipo de chamado não encontrado.")

    return _to_ticket_type_out(row)


async def update_ticket_type(
    *,
    ticket_type_id: str,
    data: TicketCatalogUpdateIn,
) -> TicketTypeOut:
    row = await TicketType.get_or_none(id=ticket_type_id)
    if not row:
        raise HTTPException(status_code=404, detail="Tipo de chamado não encontrado.")

    if data.name is not None:

        exists = await TicketType.filter(name__iexact=data.name).exclude(
            id=row.id
        ).exists()
        if exists:
            raise HTTPException(
                status_code=409,
                detail="Já existe um tipo de chamado com esse nome.",
            )

        row.name = data.name

    if data.description is not None:
        row.description = data.description

    if data.is_active is not None:
        row.is_active = data.is_active

    await row.save()
    return _to_ticket_type_out(row)


async def delete_ticket_type(*, ticket_type_id: str) -> None:
    row = await TicketType.get_or_none(id=ticket_type_id)
    if not row:
        raise HTTPException(status_code=404, detail="Tipo de chamado não encontrado.")

    row.is_active = False
    await row.save()