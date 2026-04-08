# -*- coding: utf-8 -*-
from __future__ import annotations

from collections import defaultdict
from tortoise.exceptions import IntegrityError
from tortoise.transactions import in_transaction
from fastapi import HTTPException

from app.models import User
from app.modules.tickets.application.dtos import (
    IslandListItemOut,
    TeamCreateIn,
    TeamIdNameOut,
    TeamListOut,
    TeamMemberCreateIn,
    TeamMemberOut,
    TeamMemberUpdateIn,
    TeamOut,
    TeamSimpleOut,
    TeamUpdateIn,
)
from app.modules.tickets.domain.entities import Island, Team, TeamMember


def _normalize_team_name(name: str) -> str:
    return " ".join(name.strip().split())


def _to_team_simple_out(team: Team) -> TeamSimpleOut:
    return TeamSimpleOut(
        id=str(team.id),
        created_at=team.created_at,
        name=team.name,
        description=team.description,
        is_active=team.is_active,
    )


async def _build_team_member_out(member: TeamMember) -> TeamMemberOut:
    await member.fetch_related("team", "user", "island")

    return TeamMemberOut(
        id=str(member.id),
        created_at=member.created_at,
        team_id=str(member.team.id),
        team_name=member.team.name,
        user_id=str(member.user.id),
        user_name=member.user.full_name or member.user.username,
        island_id = str(member.island.id) if member.island else None,
        island_name = member.island.name if member.island else None,
        is_active=member.is_active,
        role=member.role,
    )


async def create_team(*, data: TeamCreateIn) -> TeamSimpleOut:
    normalized_name = _normalize_team_name(data.name)

    exists = await Team.filter(name__iexact=normalized_name).exists()
    if exists:
        raise HTTPException(
            status_code=409,
            detail="Já existe uma equipe com esse nome.",
        )

    islands_data = getattr(data, "islands", []) or []

    normalized_island_names: set[str] = set()
    for island_data in islands_data:
        island_name = _normalize_team_name(island_data.name)
        if not island_name:
            raise HTTPException(
                status_code=400,
                detail="Nome da ilha é obrigatório.",
            )

        island_name_key = island_name.casefold()
        if island_name_key in normalized_island_names:
            raise HTTPException(
                status_code=409,
                detail="Existem ilhas duplicadas na requisição.",
            )
        normalized_island_names.add(island_name_key)

    async with in_transaction() as conn:
        team = await Team.create(
            name=normalized_name,
            description=data.description,
            is_active=data.is_active,
            using_db=conn,
        )

        for island_data in islands_data:
            await Island.create(
                name=_normalize_team_name(island_data.name),
                is_active=island_data.is_active,
                team_id=team.id,
                using_db=conn,
            )

    return _to_team_simple_out(team)

async def update_team(
    *,
    team_id: str,
    data: TeamUpdateIn,
) -> TeamSimpleOut:
    team = await Team.get_or_none(id=team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Equipe não encontrada.")

    if data.name is not None:
        normalized_name = _normalize_team_name(data.name)

        exists = await Team.filter(name__iexact=normalized_name).exclude(
            id=team.id
        ).exists()
        if exists:
            raise HTTPException(
                status_code=409,
                detail="Já existe uma equipe com esse nome.",
            )

    islands_data = data.islands if hasattr(data, "islands") else None

    if islands_data is not None:
        normalized_island_names: set[str] = set()

        for island_data in islands_data:
            island_name = _normalize_team_name(island_data.name)
            if not island_name:
                raise HTTPException(
                    status_code=400,
                    detail="Nome da ilha é obrigatório.",
                )

            island_name_key = island_name.casefold()
            if island_name_key in normalized_island_names:
                raise HTTPException(
                    status_code=409,
                    detail="Existem ilhas duplicadas na requisição.",
                )
            normalized_island_names.add(island_name_key)

    async with in_transaction() as conn:
        team = await Team.get_or_none(id=team_id).using_db(conn)
        if not team:
            raise HTTPException(status_code=404, detail="Equipe não encontrada.")

        if data.name is not None:
            team.name = _normalize_team_name(data.name)

        if data.description is not None:
            team.description = data.description

        if data.is_active is not None:
            team.is_active = data.is_active

        await team.save(using_db=conn)

        if islands_data is not None:
            existing_islands = await Island.filter(team_id=team.id).using_db(conn)
            existing_islands_map = {str(island.id): island for island in existing_islands}

            payload_ids: set[str] = set()

            for island_data in islands_data:
                normalized_island_name = _normalize_team_name(island_data.name)

                if island_data.id:
                    island = existing_islands_map.get(str(island_data.id))
                    if not island:
                        raise HTTPException(
                            status_code=404,
                            detail="Ilha não encontrada para esta equipe.",
                        )

                    island.name = normalized_island_name
                    island.is_active = island_data.is_active
                    await island.save(using_db=conn)

                    payload_ids.add(str(island.id))
                else:
                    new_island = await Island.create(
                        name=normalized_island_name,
                        is_active=island_data.is_active,
                        team_id=team.id,
                        using_db=conn,
                    )
                    payload_ids.add(str(new_island.id))

            for island in existing_islands:
                if str(island.id) not in payload_ids:
                    has_members = await TeamMember.filter(
                        team_id=team.id,
                        island_id=island.id,
                    ).using_db(conn).exists()

                    if has_members:
                        island.is_active = False
                        await island.save(using_db=conn)
                    else:
                        await island.delete(using_db=conn)

    return _to_team_simple_out(team)

async def delete_team(*, team_id: str) -> None:
    team = await Team.get_or_none(id=team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Equipe não encontrada.")

    if not team.is_active:
        raise HTTPException(
            status_code=400,
            detail="Equipe já está inativa.",
        )

    has_members = await TeamMember.filter(team_id=team.id).exists()
    if has_members:
        raise HTTPException(
            status_code=409,
            detail="Não é possível excluir a equipe porque ela possui membros vinculados.",
        )


    team.is_active = False
    await team.save()


async def list_teams_with_members() -> TeamListOut:
    teams = await Team.filter(is_active=True).order_by("name")

    if not teams:
        return TeamListOut(items=[], total=0)

    team_ids = [team.id for team in teams]

    members = await TeamMember.filter(team_id__in=team_ids).prefetch_related(
        "team",
        "user",
    ).order_by("team__name", "user__full_name", "user__username")

    members_by_team: dict[str, list[TeamMemberOut]] = defaultdict(list)

    for member in members:
        member_out = await _build_team_member_out(member)
        members_by_team[str(member.team_id)].append(member_out)

    raw_islands = await Island.filter(team_id__in=team_ids,is_active=True).order_by("name")
    islands_by_team: dict[str, list[IslandListItemOut]] = defaultdict(list)
    for row in raw_islands:
        islands_by_team[str(row.team_id)].append(
            IslandListItemOut(
                id=str(row.id),
                created_at=row.created_at,
                name=row.name,
                is_active=row.is_active,
            )
        )

    items = [
        TeamOut(
            id=str(team.id),
            created_at=team.created_at,
            name=team.name,
            description=team.description,
            is_active=team.is_active,
            members=members_by_team.get(str(team.id), []),
            islands=islands_by_team.get(str(team.id), []),
        )
        for team in teams
    ]

    return TeamListOut(
        items=items,
        total=len(items),
    )


async def create_team_member(*, data: TeamMemberCreateIn) -> TeamMemberOut:
    team = await Team.get_or_none(id=data.team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Equipe não encontrada.")

    user = await User.get_or_none(id=data.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    island = None
    if data.island_id:
        island = await Island.get_or_none(id=data.island_id, team_id=data.team_id, is_active=True)
        if not island:
            raise HTTPException(
            status_code=404,
            detail="Ilha não encontrada.",
            )

    if await TeamMember.filter(user_id=data.user_id).exclude(
        team_id=data.team_id
    ).exists():
        raise HTTPException(
            status_code=409,
            detail="Este usuário já está vinculado a outra equipe.",
        )

    try:
        member = await TeamMember.create(
            team_id=data.team_id,
            user_id=data.user_id,
            island_id=data.island_id,
            is_active=data.is_active,
            role=data.role,
        )
    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Usuário já está vinculado a uma equipe.",
        )

    member = await TeamMember.get(id=member.id).prefetch_related("team", "user")
    return await _build_team_member_out(member)


async def update_team_member(
    *,
    member_id: str,
    data: TeamMemberUpdateIn,
) -> TeamMemberOut:
    member = await TeamMember.get_or_none(id=member_id)
    if not member:
        raise HTTPException(
            status_code=404,
            detail="Membro da equipe não encontrado.",
        )

    has_changes = False
    member.island_id = None
    if data.island_id is not None:
        island = await Island.get_or_none(id=data.island_id)
        if not island:
            raise HTTPException(status_code=404, detail="Ilha não encontrada.")
        member.island_id = data.island_id

    if data.is_active is not None:
        member.is_active = data.is_active
        has_changes = True

    if data.role is not None:
        member.role = data.role
        has_changes = True

    if has_changes:
        await member.save()

    member = await TeamMember.get(id=member.id).prefetch_related("team", "user")
    return await _build_team_member_out(member)


async def delete_team_member(*, member_id: str) -> None:
    member = await TeamMember.get_or_none(id=member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Membro da equipe não encontrado.")

    await member.delete()

async def list_teams() -> list[TeamIdNameOut]:
    teams = await Team.filter(is_active=True).only("id", "name").order_by("name")
    
    return [
        TeamIdNameOut(
            id=str(team.id),
            name=team.name,
        )
        for team in teams
    ]