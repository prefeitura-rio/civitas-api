# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm

from app import config
from app.oidc import authenticate_user
from app.pydantic_models import Token
from app.rate_limiter import limiter

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    responses={429: {"error": "Rate limit exceeded"}},
)


@router.post("/token", response_model=Token)
@limiter.limit(config.RATE_LIMIT_DEFAULT)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    request: Request,
):
    return await authenticate_user(form_data)
