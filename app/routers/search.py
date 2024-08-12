# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.decorators import router_request
from app.dependencies import get_user
from app.models import User
from app.pydantic_models import SearchIn, SearchOut
from app.utils import search_weaviate

router = APIRouter(
    prefix="/search",
    tags=["Search"],
    responses={
        401: {"description": "You don't have permission to do this."},
        429: {"error": "Rate limit exceeded"},
    },
)


@router_request(
    method="POST",
    router=router,
    path="",
    response_model=SearchOut,
    responses={404: {"description": "Bad Request"}},
)
async def search(user: Annotated[User, Depends(get_user)], request: Request, filters: SearchIn):
    # First we need to verify that the filters are valid

    # 1. Are all filters (except for limit) None?
    if all(
        [
            filters.semantically_similar is None,
            filters.id_report is None,
            filters.id_report_original is None,
            filters.id_source is None,
            filters.data_report_min is None,
            filters.data_report_max is None,
            filters.orgaos_contains is None,
            filters.categoria is None,
            filters.categoria_contains is None,
            filters.tipo_contains is None,
            filters.subtipo_contains is None,
            filters.descricao_contains is None,
            filters.latitude_min is None,
            filters.latitude_max is None,
            filters.longitude_min is None,
            filters.longitude_max is None,
        ]
    ):
        raise HTTPException(status_code=400, detail="At least one filter must be provided.")

    # 2. If either latitude_min or latitude_max is provided, both must be provided
    if (filters.latitude_min is not None) ^ (filters.latitude_max is not None):
        raise HTTPException(
            status_code=400,
            detail="When picking latitude filter, both min and max must be specified",
        )

    # 3. If either longitude_min or longitude_max is provided, both must be providade
    if (filters.longitude_min is not None) ^ (filters.longitude_max is not None):
        raise HTTPException(
            status_code=400,
            detail="When picking longitude filter, both min and max must be specified",
        )

    return await search_weaviate(filters)
