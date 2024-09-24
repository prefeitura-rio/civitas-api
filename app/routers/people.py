# -*- coding: utf-8 -*-
import asyncio
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Request

from app.decorators import router_request
from app.dependencies import has_cpf, is_user
from app.models import PersonData, User
from app.pydantic_models import CortexCreditsOut, CortexPeopleIn, CortexPersonOut
from app.utils import get_person_details as utils_get_person_details
from app.utils import validate_cpf

router = APIRouter(
    prefix="/people",
    tags=["People"],
    responses={
        401: {"description": "You don't have permission to do this."},
        429: {"error": "Rate limit exceeded"},
    },
)


@router_request(
    method="POST",
    router=router,
    path="/",
    response_model=List[CortexPersonOut],
)
async def get_multiple_people_details(
    cpfs: CortexPeopleIn,
    user: Annotated[User, Depends(has_cpf)],
    request: Request,
):
    # Validate CPFs
    for cpf in cpfs.cpfs:
        if not validate_cpf(cpf):
            raise HTTPException(status_code=400, detail=f"Invalid CPF format: {cpf}")

    # Await for all people in batches of 10
    cpfs_list = cpfs.cpfs
    cpfs_details = []
    for i in range(0, len(cpfs_list), 10):
        cpfs_details += await asyncio.gather(
            *[
                utils_get_person_details(lookup_cpf=cpf, cpf=user.cpf)
                for cpf in cpfs_list[i : i + 10]
            ]
        )

    return cpfs_details


@router_request(
    method="POST",
    router=router,
    path="/credits",
    response_model=CortexCreditsOut,
)
async def get_necessary_credits(
    cpfs: CortexPeopleIn,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    # Check, using the provided list of CPFs, how many aren't in our database
    cpfs_data = await PersonData.filter(cpf__in=cpfs.cpfs).values_list("cpf", flat=True)
    missing_cpfs = list(set(cpfs.cpfs) - set(cpfs_data))
    return CortexCreditsOut(credits=len(missing_cpfs))


@router_request(
    method="GET",
    router=router,
    path="/{cpf}",
    response_model=CortexPersonOut,
    responses={
        400: {"detail": "Invalid CPF format"},
        451: {"detail": "Unavailable for legal reasons. CPF might be blocked."},
    },
)
async def get_person_details(
    cpf: str,
    user: Annotated[User, Depends(has_cpf)],
    request: Request,
):
    # Validate CPF
    if not validate_cpf(cpf):
        raise HTTPException(status_code=400, detail="Invalid CPF format")

    # Get CPF details
    return await utils_get_person_details(lookup_cpf=cpf, cpf=user.cpf)
