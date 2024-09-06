# -*- coding: utf-8 -*-
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi_pagination import Page, Params
from fastapi_pagination.api import create_page
from tortoise.exceptions import ValidationError

from app.decorators import router_request
from app.dependencies import is_user
from app.models import Operation, User
from app.pydantic_models import OperationIn, OperationOut, OperationUpdate

router = APIRouter(
    prefix="/operations",
    tags=["Operations"],
    responses={
        401: {"description": "You don't have permission to do this."},
        429: {"error": "Rate limit exceeded"},
    },
)


@router_request(method="GET", router=router, path="", response_model=Page[OperationOut])
async def get_operations(
    user: Annotated[User, Depends(is_user)],
    request: Request,
    params: Params = Depends(),
):
    """
    Lists all operations in the system.
    """
    offset = params.size * (params.page - 1)
    operations_queryset = await Operation.all().order_by("title").limit(params.size).offset(offset)
    operations = [OperationOut.from_orm(monitored_plate) for monitored_plate in operations_queryset]
    return create_page(operations, params=params, total=await Operation.all().count())


@router_request(method="POST", router=router, path="", response_model=OperationOut)
async def create_operation(
    operation: OperationIn,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Creates a new operation.
    """
    try:
        operation_obj = await Operation.create(**operation.dict())
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return OperationOut.from_orm(operation_obj)


@router_request(
    method="GET",
    router=router,
    path="/{operation_id}",
    response_model=OperationOut,
)
async def get_operation(
    operation_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Retrieves a operation by its ID.
    """
    operation_obj = await Operation.get_or_none(id=operation_id)
    if not operation_obj:
        raise HTTPException(status_code=404, detail="Operation not found")
    return OperationOut.from_orm(operation_obj)


@router_request(
    method="PUT",
    router=router,
    path="/{operation_id}",
    response_model=OperationOut,
)
async def update_operation(
    operation_id: UUID,
    operation_data: OperationUpdate,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Updates a operation.
    """
    operation_obj = await Operation.get_or_none(id=operation_id)
    if not operation_obj:
        raise HTTPException(status_code=404, detail="Operation not found")
    for key, value in operation_data.dict().items():
        if value is None:
            continue
        setattr(operation_obj, key, value)
    await operation_obj.save()
    return OperationOut.from_orm(operation_obj)


@router_request(
    method="DELETE",
    router=router,
    path="/{operation_id}",
    response_model=OperationOut,
)
async def delete_operation(
    operation_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Deletes a operation.
    """
    operation_obj = await Operation.get_or_none(id=operation_id)
    if not operation_obj:
        raise HTTPException(status_code=404, detail="Operation not found")
    await operation_obj.delete()
    return OperationOut.from_orm(operation_obj)
