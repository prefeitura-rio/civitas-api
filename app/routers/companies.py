# -*- coding: utf-8 -*-
from typing import Annotated, List

from fastapi import APIRouter, Depends, Request

from app.decorators import router_request
from app.dependencies import has_cpf, is_user
from app.models import User
from app.pydantic_models import CortexCompaniesIn, CortexCompanyOut, CortexCreditsOut
from app.services import CompanyService

router = APIRouter(
    prefix="/companies",
    tags=["Companies"],
    responses={
        401: {"description": "You don't have permission to do this."},
        429: {"error": "Rate limit exceeded"},
    },
)


@router_request(
    method="POST",
    router=router,
    path="/",
    response_model=List[CortexCompanyOut],
)
async def get_multiple_companies_details(
    cnpjs: CortexCompaniesIn,
    user: Annotated[User, Depends(has_cpf)],
    request: Request,
):
    """
    Get details for multiple companies by CNPJ.
    """
    return await CompanyService.get_multiple_companies_details(
        cnpjs=cnpjs.cnpjs, requester_cpf=user.cpf
    )


@router_request(
    method="POST",
    router=router,
    path="/credits",
    response_model=CortexCreditsOut,
)
async def get_necessary_credits(
    cnpjs: CortexCompaniesIn,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    """
    Calculate how many credits are needed for the given CNPJs.
    """
    credits_needed = await CompanyService.calculate_credits_needed(cnpjs.cnpjs)
    return CortexCreditsOut(credits=credits_needed)


@router_request(
    method="GET",
    router=router,
    path="/{cnpj}",
    response_model=CortexCompanyOut,
    responses={
        400: {"detail": "Invalid CNPJ format"},
        451: {"detail": "Unavailable for legal reasons. CPF might be blocked."},
    },
)
async def get_company_details(
    cnpj: str,
    user: Annotated[User, Depends(has_cpf)],
    request: Request,
):
    """
    Get details for a company by CNPJ.
    """
    return await CompanyService.get_company_details(
        cnpj=cnpj, requester_cpf=user.cpf
    )
