# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from uuid import UUID

from app.decorators import router_request
from app.dependencies import is_user
from app.models import User
from app.modules.tickets.application.dtos import (
    TeamCreateIn,
    TeamListOut,
    TeamMemberCreateIn,
    TeamMemberOut,
    TeamMemberUpdateIn,
    TeamSimpleOut,
    TeamUpdateIn,
)
from app.modules.tickets.application.services.team_service import (
    create_team,
    create_team_member,
    delete_team,
    delete_team_member,
    list_teams_with_members,
    update_team,
    update_team_member,
)

router = APIRouter(prefix="/teams", tags=["Teams"])


@router_request(
    method="GET",
    router=router,
    path="/",
    response_model=TeamListOut,
)
async def list_teams_with_members_endpoint(
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    return await list_teams_with_members()


@router_request(
    method="POST",
    router=router,
    path="/",
    response_model=TeamSimpleOut,
)
async def create_team_endpoint(
    data: TeamCreateIn,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    return await create_team(data=data)


@router_request(
    method="PUT",
    router=router,
    path="/{team_id}",
    response_model=TeamSimpleOut,
)
async def update_team_endpoint(
    team_id: UUID,
    data: TeamUpdateIn,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    return await update_team(
        team_id=str(team_id),
        data=data,
    )


@router_request(
    method="DELETE",
    router=router,
    path="/{team_id}",
    response_model=None,
)
async def delete_team_endpoint(
    team_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    await delete_team(team_id=str(team_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router_request(
    method="POST",
    router=router,
    path="/members",
    response_model=TeamMemberOut,
)
async def create_team_member_endpoint(
    data: TeamMemberCreateIn,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    return await create_team_member(data=data)


@router_request(
    method="PUT",
    router=router,
    path="/members/{member_id}",
    response_model=TeamMemberOut,
)
async def update_team_member_endpoint(
    member_id: UUID,
    data: TeamMemberUpdateIn,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    return await update_team_member(
        member_id=str(member_id),
        data=data,
    )


@router_request(
    method="DELETE",
    router=router,
    path="/members/{member_id}",
    response_model=None,
)
async def delete_team_member_endpoint(
    member_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    await delete_team_member(member_id=str(member_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)