# app/routers/tickets.py
# -*- coding: utf-8 -*-
from datetime import date
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, Query, UploadFile

from app.decorators import router_request
from app.dependencies import is_user
from app.models import User
from app.modules.tickets.application.dtos import PageOut, TicketCreateResultOut, TicketDashboardFilterIn, TicketDashboardOut, TicketFocalPointSearchOut, TicketInternalNumberSearchOut, TicketListItemOut, TicketOfficialLetterSearchOut, TicketOut, TicketProcedureNumberSearchOut, TicketRequesterSearchOut, TicketSearchOut
from app.modules.tickets.application.services.ticket_service import create_ticket, get_ticket_by_id, get_tickets_dashboard, list_tickets, parse_ticket_payload, search_focal_points, search_internal_numbers, search_official_letters, search_procedure_numbers, search_requesters, search_tickets


router = APIRouter(prefix="/tickets", tags=["Tickets"])

@router_request(
    method="POST",
    router=router,
    path="/dashboard",
    response_model=TicketDashboardOut,
)
async def get_tickets_dashboard_endpoint(
    user: Annotated[User, Depends(is_user)],
    request: Request,
    filters: TicketDashboardFilterIn,
):
    return await get_tickets_dashboard(
        user=user,
        filters=filters,
    )


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
    size: int = 20,
):
    return await list_tickets(user=user, page=page, page_size=size)

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



@router_request(
    method="GET",
    router=router,
    path="/official-letters/search",
    response_model=List[TicketOfficialLetterSearchOut],
)
async def search_official_letters_endpoint(
    user: Annotated[User, Depends(is_user)],
    request: Request,
    search: str = Query(..., min_length=2, description="Texto para buscar números de ofício"),
):
    return await search_official_letters(search=search)


@router_request(
    method="GET",
    router=router,
    path="/internal-numbers/search",
    response_model=List[TicketInternalNumberSearchOut],
)
async def search_internal_numbers_endpoint(
    user: Annotated[User, Depends(is_user)],
    request: Request,
    search: str = Query(..., min_length=2, description="Texto para buscar número interno"),
):
    return await search_internal_numbers(search=search)


@router_request(
    method="GET",
    router=router,
    path="/procedure-numbers/search",
    response_model=List[TicketProcedureNumberSearchOut],
)
async def search_procedure_numbers_endpoint(
    user: Annotated[User, Depends(is_user)],
    request: Request,
    search: str = Query(..., min_length=2, description="Texto para buscar número de procedimento"),
):
    return await search_procedure_numbers(search=search)


@router_request(
    method="GET",
    router=router,
    path="/requesters/search",
    response_model=List[TicketRequesterSearchOut],
)
async def search_requesters_endpoint(
    user: Annotated[User, Depends(is_user)],
    request: Request,
    search: str = Query(..., min_length=2, description="Texto para buscar requisitante"),
):
    return await search_requesters(search=search)


@router_request(
    method="GET",
    router=router,
    path="/focal-points/search",
    response_model=List[TicketFocalPointSearchOut],
)
async def search_focal_points_endpoint(
    user: Annotated[User, Depends(is_user)],
    request: Request,
    search: str = Query(..., min_length=2, description="Texto para buscar ponto focal"),
):
    return await search_focal_points(search=search)