from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi_pagination import Page, Params
from fastapi_pagination.api import create_page
from tortoise.exceptions import ValidationError

from app.decorators import router_request
from app.dependencies import is_user
from app.models import Demandant, Organization, User
from app.pydantic_models import DemandantIn, DemandantOut, DemandantUpdate

router = APIRouter(
    prefix="/demandants",
    tags=["Demandants"],
    responses={
        401: {"description": "You don't have permission to do this."},
        429: {"error": "Rate limit exceeded"},
    },
)


@router_request(method="GET", router=router, path="", response_model=Page[DemandantOut])
async def get_demandants(
    user: Annotated[User, Depends(is_user)],
    request: Request,
    params: Params = Depends(),
    organization_id: UUID | None = None,
):
    """
    Lists demandants, optionally filtered by organization.
    """
    offset = params.size * (params.page - 1)
    base_qs = Demandant.all().prefetch_related("organization")
    if organization_id is not None:
        base_qs = base_qs.filter(organization_id=organization_id)
    demandants_queryset = (
        await base_qs.order_by("name", "id").limit(params.size).offset(offset)
    )
    demandants = [await DemandantOut.from_demandant(d) for d in demandants_queryset]
    total_qs = Demandant.all()
    if organization_id is not None:
        total_qs = total_qs.filter(organization_id=organization_id)
    return create_page(
        demandants,
        params=params,
        total=await total_qs.count(),
    )


@router_request(method="POST", router=router, path="", response_model=DemandantOut)
async def create_demandant(
    demandant: DemandantIn,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Creates a new demandant.
    """
    organization_obj = await Organization.get_or_none(id=demandant.organization_id)
    if not organization_obj:
        raise HTTPException(status_code=404, detail="Organization not found")
    payload = demandant.dict(exclude={"organization_id"})
    try:
        demandant_obj = await Demandant.create(
            organization=organization_obj,
            **payload,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await demandant_obj.fetch_related("organization")
    return await DemandantOut.from_demandant(demandant_obj)


@router_request(
    method="GET",
    router=router,
    path="/{demandant_id}",
    response_model=DemandantOut,
)
async def get_demandant(
    demandant_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Retrieves a demandant by its ID.
    """
    demandant_obj = await Demandant.get_or_none(id=demandant_id)
    if not demandant_obj:
        raise HTTPException(status_code=404, detail="Demandant not found")
    await demandant_obj.fetch_related("organization")
    return await DemandantOut.from_demandant(demandant_obj)


@router_request(
    method="PUT",
    router=router,
    path="/{demandant_id}",
    response_model=DemandantOut,
)
async def update_demandant(
    demandant_id: UUID,
    demandant_data: DemandantUpdate,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Updates a demandant.
    """
    demandant_obj = await Demandant.get_or_none(id=demandant_id)
    if not demandant_obj:
        raise HTTPException(status_code=404, detail="Demandant not found")
    data = demandant_data.dict()
    if data.get("organization_id") is not None:
        organization_obj = await Organization.get_or_none(id=data["organization_id"])
        if not organization_obj:
            raise HTTPException(status_code=404, detail="Organization not found")
        demandant_obj.organization = organization_obj
    for key, value in data.items():
        if key == "organization_id":
            continue
        if value is None:
            continue
        setattr(demandant_obj, key, value)
    await demandant_obj.save()
    await demandant_obj.fetch_related("organization")
    return await DemandantOut.from_demandant(demandant_obj)


@router_request(
    method="DELETE",
    router=router,
    path="/{demandant_id}",
    response_model=DemandantOut,
)
async def delete_demandant(
    demandant_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Deletes a demandant.
    """
    demandant_obj = await Demandant.get_or_none(id=demandant_id)
    if not demandant_obj:
        raise HTTPException(status_code=404, detail="Demandant not found")
    await demandant_obj.fetch_related("organization")
    out = await DemandantOut.from_demandant(demandant_obj)
    await demandant_obj.delete()
    return out
