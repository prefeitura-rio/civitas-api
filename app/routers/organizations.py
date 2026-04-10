from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi_pagination import Page, Params
from fastapi_pagination.api import create_page
from tortoise.exceptions import ValidationError

from app.decorators import router_request
from app.dependencies import is_user
from app.models import Organization, User
from app.pydantic_models import OrganizationIn, OrganizationOut, OrganizationUpdate

router = APIRouter(
    prefix="/organizations",
    tags=["Organizations"],
    responses={
        401: {"description": "You don't have permission to do this."},
        429: {"error": "Rate limit exceeded"},
    },
)


@router_request(
    method="GET", router=router, path="", response_model=Page[OrganizationOut]
)
async def get_organizations(
    user: Annotated[User, Depends(is_user)],
    request: Request,
    params: Params = Depends(),
):
    """
    Lists all organizations in the system.
    """
    offset = params.size * (params.page - 1)
    organizations_queryset = (
        await Organization.all().order_by("name").limit(params.size).offset(offset)
    )
    organizations = [OrganizationOut.from_orm(org) for org in organizations_queryset]
    return create_page(
        organizations, params=params, total=await Organization.all().count()
    )


@router_request(method="POST", router=router, path="", response_model=OrganizationOut)
async def create_organization(
    organization: OrganizationIn,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Creates a new organization.
    """
    try:
        organization_obj = await Organization.create(**organization.dict())
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return OrganizationOut.from_orm(organization_obj)


@router_request(
    method="GET",
    router=router,
    path="/{organization_id}",
    response_model=OrganizationOut,
)
async def get_organization(
    organization_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Retrieves an organization by its ID.
    """
    organization_obj = await Organization.get_or_none(id=organization_id)
    if not organization_obj:
        raise HTTPException(status_code=404, detail="Organization not found")
    return OrganizationOut.from_orm(organization_obj)


@router_request(
    method="PUT",
    router=router,
    path="/{organization_id}",
    response_model=OrganizationOut,
)
async def update_organization(
    organization_id: UUID,
    organization_data: OrganizationUpdate,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Updates an organization.
    """
    organization_obj = await Organization.get_or_none(id=organization_id)
    if not organization_obj:
        raise HTTPException(status_code=404, detail="Organization not found")
    for key, value in organization_data.dict().items():
        if value is None:
            continue
        setattr(organization_obj, key, value)
    await organization_obj.save()
    return OrganizationOut.from_orm(organization_obj)


@router_request(
    method="DELETE",
    router=router,
    path="/{organization_id}",
    response_model=OrganizationOut,
)
async def delete_organization(
    organization_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Deletes an organization.
    """
    organization_obj = await Organization.get_or_none(id=organization_id)
    if not organization_obj:
        raise HTTPException(status_code=404, detail="Organization not found")
    await organization_obj.delete()
    return OrganizationOut.from_orm(organization_obj)
