# -*- coding: utf-8 -*-
from typing import Annotated, Optional
from uuid import UUID

from app.modules.tickets.application.dtos import EmailOut, EmailPageOut
from app.modules.tickets.application.services.emails_service import get_email_by_id, list_emails
from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.decorators import router_request
from app.dependencies import is_user
from app.models import User

router = APIRouter(prefix="/emails", tags=["emails"])

@router_request(
    method="get",
    router=router,
    path="/{email_id}",
    response_model=EmailOut,
)
async def get_email_by_id_endpoint(
    email_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    return await get_email_by_id(email_id)

@router_request(
    method="GET",
    router=router,
    path="/",
    response_model=EmailPageOut,
)
async def list_emails_endpoint(
    user: Annotated[User, Depends(is_user)],
    request: Request,
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
):
    return await list_emails(
        page=page,
        page_size=pageSize,
    )