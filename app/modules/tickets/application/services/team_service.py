# -*- coding: utf-8 -*-
from __future__ import annotations

from collections import defaultdict
from tortoise.exceptions import IntegrityError

from fastapi import HTTPException

from app.models import User
from app.modules.tickets.application.dtos import (
    TeamCreateIn,
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

    team = await Team.create(
        name=normalized_name,
        description=data.description,
        is_active=data.is_active,
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

        team.name = normalized_name

    if data.description is not None:
        team.description = data.description

    if data.is_active is not None:
        team.is_active = data.is_active

    await team.save()
    return _to_team_simple_out(team)


async def delete_team(*, team_id: str) -> None:
    team = await Team.get_or_none(id=team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Equipe não encontrada.")

    has_members = await TeamMember.filter(team_id=team.id).exists()
    if has_members:
        raise HTTPException(
            status_code=409,
            detail="Não é possível excluir a equipe porque ela possui membros vinculados.",
        )

    has_tickets = await team.tickets.all().exists()
    if has_tickets:
        raise HTTPException(
            status_code=409,
            detail="Não é possível excluir a equipe porque ela está vinculada a tickets.",
        )

    await team.delete()


async def list_teams_with_members() -> TeamListOut:
    teams = await Team.all().order_by("name")

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

    items = [
        TeamOut(
            id=str(team.id),
            created_at=team.created_at,
            name=team.name,
            description=team.description,
            is_active=team.is_active,
            members=members_by_team.get(str(team.id), []),
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
        island = await Island.get_or_none(id=data.island_id)
        if not island:
            raise HTTPException(status_code=404, detail="Ilha não encontrada.")

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