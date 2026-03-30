# -*- coding: utf-8 -*-
from typing import Annotated
from uuid import UUID

from app.modules.tickets.application.dtos import (
    EmailAttachmentOut,
    EmailOut,
    EmailPageOut,
    EmailSyncStatusOut,
)
from app.modules.tickets.application.services.email_sync_service import (
    get_email_sync_status,
    gmail_sync_config_ok,
    trigger_email_sync_now,
)
from app.modules.tickets.application.services.emails_service import (
    download_email_attachment,
    get_email_by_id,
    list_emails,
    mark_email_as_spam,
    upload_email_attachment,
)
from app.modules.tickets.domain.enum import EmailStatus
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
    File,
)

from app.decorators import router_request
from app.dependencies import is_user
from app.models import User

router = APIRouter(prefix="/emails", tags=["emails"])


@router_request(
    method="GET",
    router=router,
    path="/nao-lidos",
    response_model=EmailPageOut,
)
async def list_nao_lidos_endpoint(
    user: Annotated[User, Depends(is_user)],
    request: Request,
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
):
    return await list_emails(
        page=page,
        page_size=pageSize,
        statuses=[EmailStatus.NAO_LIDO],
    )


@router_request(
    method="GET",
    router=router,
    path="/respondidos",
    response_model=EmailPageOut,
)
async def list_respondidos_endpoint(
    user: Annotated[User, Depends(is_user)],
    request: Request,
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
):
    return await list_emails(
        page=page,
        page_size=pageSize,
        statuses=[EmailStatus.RESPONDIDO],
    )


@router_request(
    method="GET",
    router=router,
    path="/spam",
    response_model=EmailPageOut,
)
async def list_spam_endpoint(
    user: Annotated[User, Depends(is_user)],
    request: Request,
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
):
    return await list_emails(
        page=page,
        page_size=pageSize,
        statuses=[EmailStatus.SPAM],
    )


@router_request(
    method="GET",
    router=router,
    path="/aguardando-resposta",
    response_model=EmailPageOut,
)
async def list_aguardando_resposta_endpoint(
    user: Annotated[User, Depends(is_user)],
    request: Request,
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=10, ge=1, le=100),
):
    return await list_emails(
        page=page,
        page_size=pageSize,
        statuses=[EmailStatus.AGUARDANDO_RESPOSTA],
    )


@router_request(
    method="GET",
    router=router,
    path="/sync/status",
    response_model=EmailSyncStatusOut,
)
async def email_sync_status_endpoint(
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    raw = await get_email_sync_status()
    return EmailSyncStatusOut(**raw)


@router_request(
    method="POST",
    router=router,
    path="/sync/trigger",
)
async def email_sync_trigger_endpoint(
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    if not gmail_sync_config_ok():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sync de emails desabilitado ou credenciais Gmail incompletas.",
        )
    await trigger_email_sync_now()
    return {"detail": "Sincronização concluída."}


@router_request(
    method="PATCH",
    router=router,
    path="/{email_id}/spam",
    response_model=EmailOut,
)
async def mark_email_spam_endpoint(
    email_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    return await mark_email_as_spam(email_id=email_id)


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


@router.post("/{email_id}/attachments", response_model=EmailAttachmentOut)
async def upload_email_attachment_endpoint(
    email_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
    file: UploadFile = File(...),
):
    return await upload_email_attachment(
        email_id=email_id,
        file=file,
    )


@router_request(
    method="GET",
    router=router,
    path="/{email_id}/attachments/{attachment_id}/download",
)
async def download_email_attachment_endpoint(
    email_id: UUID,
    attachment_id: int,
    user: Annotated[User, Depends(is_user)],
    request: Request,
) -> Response:
    return await download_email_attachment(
        email_id=email_id,
        attachment_id=attachment_id,
    )
