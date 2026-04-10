# -*- coding: utf-8 -*-
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.decorators import router_request
from app.dependencies import is_user
from app.models import User
from app.modules.tickets.application.dtos import (
    StandardizedResponseCategory,
    StandardizedResponseCreateIn,
    StandardizedResponseOut,
    StandardizedResponsePageOut,
    StandardizedResponseUpdateIn,
)
from app.modules.tickets.application.services.standardized_response_service import (
    create_standardized_response,
    delete_standardized_response,
    get_standardized_response_by_id,
    list_standardized_responses,
    update_standardized_response,
)

router = APIRouter(
    prefix="/standardized-responses",
    tags=["Standardized Responses"],
)


@router_request(
    method="POST",
    router=router,
    path="/",
    response_model=StandardizedResponseOut,
)
async def create_standardized_response_endpoint(
    data: StandardizedResponseCreateIn,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    return await create_standardized_response(data=data)


@router_request(
    method="GET",
    router=router,
    path="/",
    response_model=StandardizedResponsePageOut,
)
async def list_standardized_responses_endpoint(
    user: Annotated[User, Depends(is_user)],
    request: Request,
    search: Optional[str] = Query(default=None),
    category: Optional[StandardizedResponseCategory] = Query(default=None),
    isActive: Optional[bool] = Query(default=None),
):
    return await list_standardized_responses(
        search=search,
        category=category.value if category else None,
        is_active=isActive,
    )


@router_request(
    method="GET",
    router=router,
    path="/{standardized_response_id}",
    response_model=StandardizedResponseOut,
)
async def get_standardized_response_endpoint(
    standardized_response_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    return await get_standardized_response_by_id(
        standardized_response_id=str(standardized_response_id),
    )


@router_request(
    method="PUT",
    router=router,
    path="/{standardized_response_id}",
    response_model=StandardizedResponseOut,
)
async def update_standardized_response_endpoint(
    standardized_response_id: UUID,
    data: StandardizedResponseUpdateIn,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    return await update_standardized_response(
        standardized_response_id=str(standardized_response_id),
        data=data,
    )


@router_request(
    method="DELETE",
    router=router,
    path="/{standardized_response_id}",
    response_model=None,
)
async def delete_standardized_response_endpoint(
    standardized_response_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    await delete_standardized_response(
        standardized_response_id=str(standardized_response_id),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)