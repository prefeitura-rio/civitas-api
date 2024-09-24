# -*- coding: utf-8 -*-
import asyncio
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Request

from app.decorators import router_request
from app.dependencies import has_cpf, is_user
from app.models import CompanyData, User
from app.pydantic_models import CortexCompaniesIn, CortexCompanyOut, CortexCreditsOut
from app.utils import get_company_details as utils_get_company_details
from app.utils import validate_cnpj

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
    # Validate CNPJs
    for cnpj in cnpjs.cnpjs:
        if not validate_cnpj(cnpj):
            raise HTTPException(status_code=400, detail=f"Invalid CNPJ format: {cnpj}")

    # Await for all companies in batches of 10
    cnpjs_list = cnpjs.cnpjs
    cnpjs_details = []
    for i in range(0, len(cnpjs_list), 10):
        cnpjs_details += await asyncio.gather(
            *[utils_get_company_details(cnpj=cnpj, cpf=user.cpf) for cnpj in cnpjs_list[i : i + 10]]
        )

    return cnpjs_details


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
    # Check, using the provided list of CNPJs, how many aren't in our database
    cnpjs_data = await CompanyData.filter(cnpj__in=cnpjs.cnpjs).values_list("cnpj", flat=True)
    missing_cnpjs = list(set(cnpjs.cnpjs) - set(cnpjs_data))
    return CortexCreditsOut(credits=len(missing_cnpjs))


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
    # Validate CNPJ
    if not validate_cnpj(cnpj):
        raise HTTPException(status_code=400, detail="Invalid CNPJ format")

    # Get CNPJ details
    return await utils_get_company_details(cnpj=cnpj, cpf=user.cpf)
