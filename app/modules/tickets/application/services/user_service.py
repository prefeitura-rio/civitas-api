# -*- coding: utf-8 -*-
from __future__ import annotations

from collections import defaultdict

from fastapi import HTTPException
from tortoise.expressions import Q
from tortoise.transactions import in_transaction

from app.models import User
from app.modules.tickets.application.dtos import (
    UserRoleListItemOut,
    UserRoleOut,
    UserRolePageOut,
    UserRoleUpdateIn,
)
from app.modules.tickets.domain.entities import UserRole
from app.modules.tickets.domain.enum import UserRoleEnum


def _deduplicate_roles(roles: list[UserRoleEnum]) -> list[UserRoleEnum]:
    seen = set()
    result: list[UserRoleEnum] = []

    for role in roles:
        if role not in seen:
            seen.add(role)
            result.append(role)

    return result


async def _build_user_role_out(user: User) -> UserRoleOut:
    await user.fetch_related("roles")

    ordered_roles = sorted(
        [item.role for item in user.roles],
        key=lambda x: x.value,
    )

    return UserRoleOut(
        id=str(user.id),
        username=user.username,
        full_name=user.full_name,
        email=user.email,
        roles=ordered_roles,
    )


async def list_users_with_roles(
    *,
    page: int = 1,
    page_size: int = 10,
    search: str | None = None,
) -> UserRolePageOut:
    if page < 1:
        raise HTTPException(status_code=400, detail="Página inválida.")

    if page_size < 1 or page_size > 100:
        raise HTTPException(status_code=400, detail="page_size deve estar entre 1 e 100.")

    termo = (search or "").strip()
    if termo:
        query = User.filter(
            Q(username__icontains=termo)
            | Q(full_name__icontains=termo)
            | Q(email__icontains=termo)
        )
    else:
        query = User.all()

    total = await query.count()

    offset = (page - 1) * page_size
    users = await query.order_by("full_name", "username").offset(offset).limit(page_size)

    if not users:
        return UserRolePageOut(items=[], total=total)

    user_ids = [user.id for user in users]

    role_rows = await UserRole.filter(user_id__in=user_ids).order_by("role")

    roles_by_user: dict[str, list[UserRoleEnum]] = defaultdict(list)
    for row in role_rows:
        roles_by_user[str(row.user_id)].append(row.role)

    items = [
        UserRoleListItemOut(
            id=str(user.id),
            username=user.username,
            full_name=user.full_name,
            email=user.email,
            roles=roles_by_user.get(str(user.id), []),
        )
        for user in users
    ]

    return UserRolePageOut(
        items=items,
        total=total,
    )


async def list_users_only_with_roles() -> list[UserRoleListItemOut]:
    role_rows = await UserRole.all().order_by("role")

    if not role_rows:
        return []

    user_ids = list({row.user_id for row in role_rows})

    users = await User.filter(id__in=user_ids).order_by("full_name", "username")

    roles_by_user: dict[str, list[UserRoleEnum]] = defaultdict(list)
    for row in role_rows:
        roles_by_user[str(row.user_id)].append(row.role)

    items = [
        UserRoleListItemOut(
            id=str(user.id),
            username=user.username,
            full_name=user.full_name,
            email=user.email,
            roles=roles_by_user.get(str(user.id), []),
        )
        for user in users
    ]

    return items


async def update_user_roles(
    *,
    user_id: str,
    data: UserRoleUpdateIn,
) -> UserRoleOut:
    user = await User.get_or_none(id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    roles = _deduplicate_roles(data.roles)

    async with in_transaction():
        await UserRole.filter(user_id=user.id).delete()

        if roles:
            await UserRole.bulk_create(
                [
                    UserRole(
                        user_id=user.id,
                        role=role,
                    )
                    for role in roles
                ]
            )

    return await _build_user_role_out(user)


async def get_user_roles_by_id(
    *,
    user_id: str,
) -> UserRoleOut:
    user = await User.get_or_none(id=user_id)

    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    return await _build_user_role_out(user)