# -*- coding: utf-8 -*-
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.decorators import router_request
from app.dependencies import is_user
from app.models import User
from app.modules.tickets.application.dtos import (
    EmailTemplateCreateIn,
    EmailTemplateOut,
    EmailTemplatePageOut,
    EmailTemplateUpdateIn,
)
from app.modules.tickets.application.services.email_template_service import (
    create_email_template,
    delete_email_template,
    get_email_template_by_id,
    list_email_templates,
    update_email_template,
)

router = APIRouter(prefix="/emails", tags=["email-templates"])


@router_request(
    method="GET",
    router=router,
    path="/templates",
    response_model=EmailTemplatePageOut,
)
async def list_email_templates_endpoint(
    user: Annotated[User, Depends(is_user)],
    request: Request,
    search: Optional[str] = Query(default=None),
    isActive: Optional[bool] = Query(default=None),
):
    return await list_email_templates(search=search, is_active=isActive)


@router_request(
    method="POST",
    router=router,
    path="/templates",
    response_model=EmailTemplateOut,
)
async def create_email_template_endpoint(
    user: Annotated[User, Depends(is_user)],
    request: Request,
    data: EmailTemplateCreateIn,
):
    return await create_email_template(data=data)


@router_request(
    method="GET",
    router=router,
    path="/templates/{template_id}",
    response_model=EmailTemplateOut,
)
async def get_email_template_endpoint(
    template_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    return await get_email_template_by_id(template_id=str(template_id))


@router_request(
    method="PUT",
    router=router,
    path="/templates/{template_id}",
    response_model=EmailTemplateOut,
)
async def update_email_template_endpoint(
    template_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
    data: EmailTemplateUpdateIn,
):
    return await update_email_template(template_id=str(template_id), data=data)


@router_request(
    method="DELETE",
    router=router,
    path="/templates/{template_id}",
    response_model=None,
)
async def delete_email_template_endpoint(
    template_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    await delete_email_template(template_id=str(template_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
