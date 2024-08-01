# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.decorators import router_request
from app.dependencies import get_user
from app.models import User
from app.pydantic_models import SearchIn, SearchOut

router = APIRouter(
    prefix="/search",
    tags=["Search"],
    responses={
        401: {"description": "You don't have permission to do this."},
        429: {"error": "Rate limit exceeded"},
    },
)


@router_request(method="POST", router=router, path="", response_model=SearchOut)
async def get_cameras_list(
    user: Annotated[User, Depends(get_user)], request: Request, filters: SearchIn
):
    raise NotImplementedError("TO DO.")
