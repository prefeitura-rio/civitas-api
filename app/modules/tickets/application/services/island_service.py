# -*- coding: utf-8 -*-
from __future__ import annotations

from fastapi import HTTPException
from tortoise.expressions import Q

from app.modules.tickets.application.dtos import (
    IslandCreateIn,
    TicketCatalogUpdateIn,
    IslandListItemOut,
    IslandOut,
    IslandPageOut,
)
from app.modules.tickets.domain.entities import Island, Team


def _normalize_name(name: str) -> str:
    return " ".join(name.strip().split())


def _to_island_out(row: Island) -> IslandOut:
    return IslandOut(
        id=str(row.id),
        created_at=row.created_at,
        name=row.name,
        is_active=row.is_active,
    )


async def create_island(*, data: IslandCreateIn) -> IslandOut:
    team = await Team.get_or_none(id=data.team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Equipe não encontrada.")

    normalized_name = _normalize_name(data.name)

    exists = await Island.filter(
        team_id=data.team_id,
        name__iexact=normalized_name,
    ).exists()
    if exists:
        raise HTTPException(
            status_code=409,
            detail="Já existe uma ilha com esse nome nesta equipe.",
        )

    row = await Island.create(
        team_id=data.team_id,
        name=normalized_name,
        is_active=data.is_active,
    )

    return _to_island_out(row)


async def list_islands(
    *,
    search: str | None = None,
    is_active: bool | None = None,
) -> IslandPageOut:
    query = Island.all()

    if search and search.strip():
        termo = search.strip()
        query = query.filter(
            Q(name__icontains=termo)
        )

    if is_active is not None:
        query = query.filter(is_active=is_active)

    total = await query.count()
    rows = await query.order_by("name")

    items = [
        IslandListItemOut(
            id=str(row.id),
            created_at=row.created_at,
            name=row.name,
            is_active=row.is_active,
        )
        for row in rows
    ]

    return IslandPageOut(
        items=items,
        total=total,
    )

async def list_islands_by_team(
    *,
    team_id: str,
    search: str | None = None,
    is_active: bool | None = None,
) -> IslandPageOut:
    query = Island.filter(team_id=team_id)

    if search and search.strip():
        termo = search.strip()
        query = query.filter(
            Q(name__icontains=termo)
        )

    if is_active is not None:
        query = query.filter(is_active=is_active)

    total = await query.count()
    rows = await query.order_by("name")

    items = [
        IslandListItemOut(
            id=str(row.id),
            created_at=row.created_at,
            name=row.name,
            is_active=row.is_active,
        )
        for row in rows
    ]

    return IslandPageOut(
        items=items,
        total=total,
    )


async def get_island_by_id(*, island_id: str) -> IslandOut:
    row = await Island.get_or_none(id=island_id)
    if not row:
        raise HTTPException(status_code=404, detail="Ilha não encontrada.")

    return _to_island_out(row)


async def update_island(
    *,
    island_id: str,
    data: TicketCatalogUpdateIn,
) -> IslandOut:
    row = await Island.get_or_none(id=island_id)
    if not row:
        raise HTTPException(status_code=404, detail="Ilha não encontrada.")

    if data.name is not None:
        normalized_name = _normalize_name(data.name)

        exists = await Island.filter(
            team_id=row.team_id,
            name__iexact=normalized_name,
        ).exclude(id=row.id).exists()
        if exists:
            raise HTTPException(
                status_code=409,
                detail="Já existe uma ilha com esse nome nesta equipe.",
            )

        row.name = normalized_name


    if data.is_active is not None:
        row.is_active = data.is_active

    await row.save()
    return _to_island_out(row)


async def delete_island(*, island_id: str) -> None:
    row = await Island.get_or_none(id=island_id)
    if not row:
        raise HTTPException(status_code=404, detail="Ilha não encontrada.")

    has_team_members = await row.team_members.all().exists()
    if has_team_members:
        raise HTTPException(
            status_code=409,
            detail="Não é possível excluir a ilha porque ela está vinculada a membros de equipe.",
        )

    await row.delete()