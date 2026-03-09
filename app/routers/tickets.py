# app/routers/tickets.py
# -*- coding: utf-8 -*-
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, Query, UploadFile

from app.decorators import router_request
from app.dependencies import is_user
from app.models import User
from app.modules.tickets.application.dtos import PageOut, TicketCreateResultOut, TicketListItemOut, TicketOut, TicketSearchOut
from app.modules.tickets.application.services.ticket_service import create_ticket, get_ticket_by_id, list_tickets, parse_ticket_payload, search_tickets


router = APIRouter(prefix="/tickets", tags=["Tickets"])

@router.post("/", response_model=TicketCreateResultOut)
async def create_ticket_endpoint(
    payload: Annotated[str, Form(...)],
    files: Annotated[Optional[List[UploadFile]], File()] = None,
    user: Annotated[User, Depends(is_user)] = None,
    request: Request = None,
):
    ticket_in = parse_ticket_payload(payload)
    return await create_ticket(ticket_in=ticket_in, author=user, files=files or [])


@router.get("/search", response_model=List[TicketSearchOut])
async def search_tickets_endpoint(
    search: str = Query(..., min_length=1, description="Texto para buscar tickets"),
):
    return await search_tickets(search=search)


@router_request(
    method="GET",
    router=router,
    path="/",
    response_model=PageOut,
)
async def list_tickets_endpoint(
    user: Annotated[User, Depends(is_user)],
    request: Request,
    page: int = 1,
    page_size: int = 20,
):
    return await list_tickets(user=user, page=page, page_size=page_size)

@router_request(
    method="GET",
    router=router,
    path="/{ticket_id}",
    response_model=TicketOut,
)
async def get_ticket_endpoint(
    ticket_id: UUID,
    user: Annotated[User, Depends(is_user)],
    request: Request,
):
    return await get_ticket_by_id(ticket_id=ticket_id)

