# -*- coding: utf-8 -*-
import asyncio
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi_pagination import Page, Params
from fastapi_pagination.api import create_page
from tortoise.transactions import in_transaction

from app.decorators import router_request
from app.dependencies import is_user, is_admin
from app.models import Group, GroupUser, Permission, Resource, Role, User
from app.pydantic_models import (
    GroupIn,
    GroupOut,
    GroupUpdate,
    GroupUserIn,
    GroupUserOut,
    GroupUserUpdate,
    PermissionIn,
    PermissionOut,
    ResourceOut,
    RoleIn,
    RoleOut,
    RolePermissionIn,
    RoleUpdate,
    RoleUserIn,
    UserOut,
)
from app.utils import user_is_group_admin, user_is_group_member

router = APIRouter(
    prefix="/rbac",
    tags=["RBAC and groups management"],
    responses={
        401: {"description": "You don't have permission to do this."},
        404: {"description": "Not found"},
        429: {"error": "Rate limit exceeded"},
    },
)


@router_request(
    method="GET", router=router, path="/groups", response_model=Page[GroupOut]
)
async def list_groups(
    user: Annotated[User, Depends(is_admin)],
    request: Request,
    params: Params = Depends(),
):
    """
    Lists all groups in the system.
    """
    offset = params.size * (params.page - 1)
    groups_queryset = await Group.all().limit(params.size).offset(offset)
    groups = [GroupOut.from_group(group) for group in groups_queryset]
    groups = await asyncio.gather(*groups)
    return create_page(groups, params=params, total=await Group.all().count())


@router_request(method="POST", router=router, path="/groups", response_model=GroupOut)
async def create_group(
    group: GroupIn,
    user: Annotated[User, Depends(is_admin)],
    request: Request,
):
    """
    Creates a new group.
    """
    group_user_ids = group.users or []
    if not group_user_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must provide at least one user for the group.",
        )

    async with in_transaction():
        group_obj = await Group.create(name=group.name, description=group.description)
        for user_id in group_user_ids:
            user_obj = await User.get_or_none(id=user_id)
            if not user_obj:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found.",
                )
            await GroupUser.create(group=group_obj, user=user_obj)

    return await GroupOut.from_group(group_obj)


@router_request(
    method="GET",
    router=router,
    path="/groups/{group_id}",
    response_model=GroupOut,
    responses={
        404: {"description": "Group not found"},
    },
)
async def get_group(
    group_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Retrieves a group by its ID.
    """
    if not await user_is_group_member(group_id, user):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don't have permission to do this.",
        )
    group_obj = await Group.get_or_none(id=group_id)
    if not group_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found.",
        )
    return await GroupOut.from_group(group_obj)


@router_request(
    method="PUT",
    router=router,
    path="/groups/{group_id}",
    response_model=GroupOut,
    responses={
        404: {"description": "Group not found"},
    },
)
async def update_group(
    group_id: UUID,
    group_data: GroupUpdate,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Updates a group by its ID.
    """
    if not await user_is_group_admin(group_id, user):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don't have permission to do this.",
        )
    group = await Group.get_or_none(id=group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    for key, value in group_data.dict().items():
        if value is None:
            continue
        setattr(group, key, value)
    await group.save()
    return await GroupOut.from_group(group)


@router_request(
    method="DELETE",
    router=router,
    path="/groups/{group_id}",
    responses={
        404: {"description": "Group not found"},
    },
    response_model=GroupOut,
)
async def delete_group(
    group_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Deletes a group by its ID.
    """
    if not await user_is_group_admin(group_id, user):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don't have permission to do this.",
        )
    group = await Group.get_or_none(id=group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    await group.delete()
    return await GroupOut.from_group(group)


@router_request(
    method="GET",
    router=router,
    path="/groups/{group_id}/permissions",
    response_model=Page[PermissionOut],
    responses={
        404: {"description": "Group not found"},
    },
)
async def list_group_permissions(
    group_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
    params: Params = Depends(),
):
    """
    Lists all permissions in a group by its ID.
    """
    if not await user_is_group_member(group_id, user):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don't have permission to do this.",
        )
    group = await Group.get_or_none(id=group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    offset = params.size * (params.page - 1)
    permissions = (
        await Permission.filter(group=group)
        .prefetch_related("resource")
        .all()
        .limit(params.size)
        .offset(offset)
    )
    permissions = [PermissionOut.from_orm(permission) for permission in permissions]
    return create_page(
        permissions,
        params=params,
        total=await Permission.filter(group=group)
        .prefetch_related("resource")
        .all()
        .count(),
    )


@router_request(
    method="POST",
    router=router,
    path="/groups/{group_id}/permissions",
    response_model=PermissionOut,
    responses={
        404: {"description": "Group not found"},
    },
)
async def add_permission_to_group(
    group_id: UUID,
    permission: PermissionIn,
    user: Annotated[User, Depends(is_admin)],
    request: Request,
):
    """
    Adds a permission to a group by its ID.
    """
    group = await Group.get_or_none(id=group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    resource = await Resource.get_or_none(id=permission.resource)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    permission_obj = await Permission.create(
        action=permission.action, group=group, resource=resource
    )
    return PermissionOut.from_orm(permission_obj)


@router_request(
    method="DELETE",
    router=router,
    path="/groups/{group_id}/permissions/{permission_id}",
    responses={
        404: {"description": "Group or permission not found"},
    },
    response_model=PermissionOut,
)
async def delete_group_permission(
    group_id: UUID,
    permission_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Deletes a permission from a group by their IDs.
    """
    if not await user_is_group_admin(group_id, user):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don't have permission to do this.",
        )
    group = await Group.get_or_none(id=group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    permission = await Permission.get_or_none(id=permission_id)
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")
    await permission.delete()
    return PermissionOut.from_orm(permission)


@router_request(
    method="GET",
    router=router,
    path="/groups/{group_id}/roles",
    response_model=Page[RoleOut],
    responses={
        404: {"description": "Group not found"},
    },
)
async def list_group_roles(
    group_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
    params: Params = Depends(),
):
    """
    Lists all roles in a group by its ID.
    """
    if not await user_is_group_member(group_id, user):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don't have permission to do this.",
        )
    group = await Group.get_or_none(id=group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    offset = params.size * (params.page - 1)
    roles = (
        await Role.filter(group=group)
        .prefetch_related("users", "permissions")
        .all()
        .limit(params.size)
        .offset(offset)
    )
    roles = [RoleOut.from_orm(role) for role in roles]
    return create_page(
        roles,
        params=params,
        total=await Role.filter(group=group)
        .prefetch_related("users", "permissions")
        .all()
        .count(),
    )


@router_request(
    method="POST",
    router=router,
    path="/groups/{group_id}/roles",
    response_model=RoleOut,
    responses={
        404: {"description": "Group not found"},
    },
)
async def add_role_to_group(
    group_id: UUID,
    role: RoleIn,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Creates a role to a group by its ID.
    """
    if not await user_is_group_admin(group_id, user):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don't have permission to do this.",
        )
    group = await Group.get_or_none(id=group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    role_obj = await Role.create(name=role.name, group=group)
    return RoleOut.from_orm(role_obj)


@router_request(
    method="GET",
    router=router,
    path="/groups/{group_id}/roles/{role_id}",
    response_model=RoleOut,
    responses={
        404: {"description": "Group or role not found"},
    },
)
async def get_group_role(
    group_id: UUID,
    role_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Retrieves a role in a group by their IDs.
    """
    if not await user_is_group_member(group_id, user):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don't have permission to do this.",
        )
    group = await Group.get_or_none(id=group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    role = await Role.get_or_none(id=role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return RoleOut.from_orm(role)


@router_request(
    method="PUT",
    router=router,
    path="/groups/{group_id}/roles/{role_id}",
    response_model=RoleOut,
    responses={
        404: {"description": "Group or role not found"},
    },
)
async def update_group_role(
    group_id: UUID,
    role_id: UUID,
    role_data: RoleUpdate,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Updates a role in a group by their IDs.
    """
    if not await user_is_group_admin(group_id, user):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don't have permission to do this.",
        )
    group = await Group.get_or_none(id=group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    role = await Role.get_or_none(id=role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    for key, value in role_data.dict().items():
        if value is None:
            continue
        setattr(role, key, value)
    await role.save()
    return RoleOut.from_orm(role)


@router_request(
    method="DELETE",
    router=router,
    path="/groups/{group_id}/roles/{role_id}",
    responses={
        404: {"description": "Group or role not found"},
    },
    response_model=RoleOut,
)
async def delete_group_role(
    group_id: UUID,
    role_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Deletes a role from a group by their IDs.
    """
    if not await user_is_group_admin(group_id, user):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don't have permission to do this.",
        )
    group = await Group.get_or_none(id=group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    role = await Role.get_or_none(id=role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    await role.delete()
    return RoleOut.from_orm(role)


@router_request(
    method="GET",
    router=router,
    path="/groups/{group_id}/roles/{role_id}/permissions",
    response_model=Page[PermissionOut],
    responses={
        404: {"description": "Group or role not found"},
    },
)
async def list_group_role_permissions(
    group_id: UUID,
    role_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
    params: Params = Depends(),
):
    """
    Lists all permissions in a role in a group by their IDs.
    """
    if not await user_is_group_member(group_id, user):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don't have permission to do this.",
        )
    group = await Group.get_or_none(id=group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    role = await Role.get_or_none(id=role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    offset = params.size * (params.page - 1)
    permissions = (
        await Permission.filter(group=group, role=role)
        .prefetch_related("resource")
        .all()
        .limit(params.size)
        .offset(offset)
    )
    permissions = [PermissionOut.from_orm(permission) for permission in permissions]
    return create_page(
        permissions,
        params=params,
        total=await Permission.filter(group=group, role=role)
        .prefetch_related("resource")
        .all()
        .count(),
    )


@router_request(
    method="POST",
    router=router,
    path="/groups/{group_id}/roles/{role_id}/permissions",
    response_model=PermissionOut,
    responses={
        404: {"description": "Group or role not found"},
    },
)
async def add_permission_to_group_role(
    group_id: UUID,
    role_id: UUID,
    role_permission: RolePermissionIn,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Adds a permission to a role in a group by their IDs.
    """
    if not await user_is_group_admin(group_id, user):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don't have permission to do this.",
        )
    group = await Group.get_or_none(id=group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    role = await Role.get_or_none(id=role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    resource = await Resource.get_or_none(id=role_permission.permission)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    permission_obj = await Permission.create(
        action=role_permission.action, group=group, role=role, resource=resource
    )
    return PermissionOut.from_orm(permission_obj)


@router_request(
    method="DELETE",
    router=router,
    path="/groups/{group_id}/roles/{role_id}/permissions/{permission_id}",
    responses={
        404: {"description": "Group, role or permission not found"},
    },
    response_model=PermissionOut,
)
async def delete_permission_from_group_role(
    group_id: UUID,
    role_id: UUID,
    permission_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Deletes a permission from a role in a group by their IDs.
    """
    if not await user_is_group_admin(group_id, user):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don't have permission to do this.",
        )
    group = await Group.get_or_none(id=group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    role = await Role.get_or_none(id=role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    permission = await Permission.get_or_none(id=permission_id)
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")
    await permission.delete()
    return PermissionOut.from_orm(permission)


@router_request(
    method="GET",
    router=router,
    path="/groups/{group_id}/roles/{role_id}/users",
    response_model=Page[GroupUserOut],
    responses={
        404: {"description": "Group or role not found"},
    },
)
async def list_group_role_users(
    group_id: UUID,
    role_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
    params: Params = Depends(),
):
    """
    Lists all users in a role in a group by their IDs.
    """
    if not await user_is_group_member(group_id, user):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don't have permission to do this.",
        )
    group = await Group.get_or_none(id=group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    role = await Role.get_or_none(id=role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    offset = params.size * (params.page - 1)
    role_users = (
        await role.users.prefetch_related("user")
        .all()
        .limit(params.size)
        .offset(offset)
    )
    users = [
        GroupUserOut(
            user=UserOut.from_orm(role_user.user),
            is_group_admin=role_user.is_group_admin,
        )
        for role_user in role_users
    ]
    return create_page(
        users,
        params=params,
        total=await role.users.prefetch_related("user").all().count(),
    )


@router_request(
    method="POST",
    router=router,
    path="/groups/{group_id}/roles/{role_id}/users",
    response_model=RoleOut,
    responses={
        404: {"description": "Group or role not found"},
    },
)
async def add_user_to_group_role(
    group_id: UUID,
    role_id: UUID,
    role_user: RoleUserIn,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Adds a user to a role in a group by their IDs.
    """
    if not await user_is_group_admin(group_id, user):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don't have permission to do this.",
        )
    group = await Group.get_or_none(id=group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    role = await Role.get_or_none(id=role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    user_obj = await User.get_or_none(id=role_user.user)
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")
    await role.users.add(user_obj)
    return RoleOut.from_orm(role)


@router_request(
    method="DELETE",
    router=router,
    path="/groups/{group_id}/roles/{role_id}/users/{user_id}",
    responses={
        404: {"description": "Group, role or user not found"},
    },
    response_model=RoleOut,
)
async def delete_user_from_group_role(
    group_id: UUID,
    role_id: UUID,
    user_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Deletes a user from a role in a group by their IDs.
    """
    if not await user_is_group_admin(group_id, user):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don't have permission to do this.",
        )
    group = await Group.get_or_none(id=group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    role = await Role.get_or_none(id=role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    user_obj = await User.get_or_none(id=user_id)
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")
    await role.users.remove(user_obj)
    return RoleOut.from_orm(role)


@router_request(
    method="GET",
    router=router,
    path="/groups/{group_id}/users",
    response_model=Page[GroupUserOut],
    responses={
        404: {"description": "Group not found"},
    },
)
async def list_group_users(
    group_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
    params: Params = Depends(),
):
    """
    Lists all users in a group by its ID.
    """
    if not await user_is_group_member(group_id, user):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don't have permission to do this.",
        )
    group = await Group.get_or_none(id=group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    offset = params.size * (params.page - 1)
    group_users = (
        await GroupUser.filter(group=group)
        .prefetch_related("user")
        .all()
        .limit(params.size)
        .offset(offset)
    )
    users = [
        GroupUserOut(
            user=UserOut.from_orm(group_user.user),
            is_group_admin=group_user.is_group_admin,
        )
        for group_user in group_users
    ]
    return create_page(
        users,
        params=params,
        total=await GroupUser.filter(group=group)
        .prefetch_related("user")
        .all()
        .count(),
    )


@router_request(
    method="POST",
    router=router,
    path="/groups/{group_id}/users",
    response_model=GroupUserOut,
    responses={
        404: {"description": "Group not found"},
    },
)
async def add_user_to_group(
    group_id: UUID,
    group_user: GroupUserIn,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Adds a user to a group by their ID.
    """
    if not await user_is_group_admin(group_id, user):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don't have permission to do this.",
        )
    group = await Group.get_or_none(id=group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    user_obj = await User.get_or_none(id=group_user.user)
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")
    group_user_obj = await GroupUser.create(
        group=group, user=user_obj, is_group_admin=group_user.is_group_admin
    )
    return GroupUserOut(
        user=UserOut.from_orm(user_obj), is_group_admin=group_user_obj.is_group_admin
    )


@router_request(
    method="GET",
    router=router,
    path="/groups/{group_id}/users/{user_id}",
    response_model=GroupUserOut,
    responses={
        404: {"description": "Group or user not found"},
    },
)
async def get_group_user(
    group_id: UUID,
    user_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Retrieves a user in a group by their IDs.
    """
    if not await user_is_group_member(group_id, user):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don't have permission to do this.",
        )
    group = await Group.get_or_none(id=group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    user_obj = await User.get_or_none(id=user_id)
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")
    group_user = await GroupUser.get_or_none(group=group, user=user_obj)
    if not group_user:
        raise HTTPException(status_code=404, detail="User not found in the group")
    return GroupUserOut(
        user=UserOut.from_orm(user_obj), is_group_admin=group_user.is_group_admin
    )


@router_request(
    method="PUT",
    router=router,
    path="/groups/{group_id}/users/{user_id}",
    response_model=GroupUserOut,
    responses={
        404: {"description": "Group or user not found"},
    },
)
async def update_group_user(
    group_id: UUID,
    user_id: UUID,
    group_user_data: GroupUserUpdate,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Updates a user in a group by their IDs.
    """
    if not await user_is_group_admin(group_id, user):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don't have permission to do this.",
        )
    group = await Group.get_or_none(id=group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    user_obj = await User.get_or_none(id=user_id)
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")
    group_user = await GroupUser.get_or_none(group=group, user=user_obj)
    if not group_user:
        raise HTTPException(status_code=404, detail="User not found in the group")
    for key, value in group_user_data.dict().items():
        if value is None:
            continue
        setattr(group_user, key, value)
    await group_user.save()
    return GroupUserOut(
        user=UserOut.from_orm(user_obj), is_group_admin=group_user.is_group_admin
    )


@router_request(
    method="DELETE",
    router=router,
    path="/groups/{group_id}/users/{user_id}",
    responses={
        404: {"description": "Group or user not found"},
    },
    response_model=GroupUserOut,
)
async def delete_group_user(
    group_id: UUID,
    user_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Deletes a user from a group by their IDs.
    """
    if not await user_is_group_admin(group_id, user):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don't have permission to do this.",
        )
    group = await Group.get_or_none(id=group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    user_obj = await User.get_or_none(id=user_id)
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")
    group_user = await GroupUser.get_or_none(group=group, user=user_obj)
    if not group_user:
        raise HTTPException(status_code=404, detail="User not found in the group")
    await group_user.delete()
    return GroupUserOut(
        user=UserOut.from_orm(user_obj), is_group_admin=group_user.is_group_admin
    )


@router_request(
    method="GET",
    router=router,
    path="/resources",
    response_model=Page[ResourceOut],
)
async def list_resources(
    user: Annotated[User, Depends(is_user)],
    request: Request,
    params: Params = Depends(),
):
    """
    Lists all resources in the system.
    """
    offset = params.size * (params.page - 1)
    resources = [
        ResourceOut.from_orm(resource)
        for resource in await Resource.all().limit(params.size).offset(offset)
    ]
    return create_page(resources, params=params, total=await Resource.all().count())
