# -*- coding: utf-8 -*-
from typing import Annotated, List

from fastapi import APIRouter, Depends, Request

from app.decorators import router_request
from app.dependencies import has_cpf, is_user
from app.models import User
from app.pydantic_models import CortexCreditsOut, CortexPeopleIn, CortexPersonOut
from app.services import PeopleService

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
    """
    Get details for multiple people by CPF.
    """
    return await PeopleService.get_multiple_people_details(
        cpfs=cpfs.cpfs, requester_cpf=user.cpf
    )


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
    """
    Calculate how many credits are needed for the given CPFs.
    """
    credits_needed = await PeopleService.calculate_credits_needed(cpfs.cpfs)
    return CortexCreditsOut(credits=credits_needed)


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
    """
    Get details for a person by CPF.
    """
    return await PeopleService.get_person_details(
        lookup_cpf=cpf, requester_cpf=user.cpf
    )
