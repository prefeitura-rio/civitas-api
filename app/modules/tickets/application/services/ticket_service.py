# -*- coding: utf-8 -*-

from datetime import datetime, timedelta, time, timezone
import json
import uuid
from typing import List, Optional, Tuple

from app.config import GCS_BUCKET_NAME
from app.modules.tickets.domain.enum import TicketPriority, TicketStatus
from app.modules.tickets.infrastructure.gcs_upload import (
    build_ticket_object_name,
    gcs_delete_objects,
    gcs_upload_file_bytes,
)
from tortoise.transactions import in_transaction
from fastapi import HTTPException, UploadFile
from loguru import logger
from pydantic import ValidationError
from tortoise.expressions import Q

from app.models import Operation, User
from app.modules.tickets.application.dtos import (
    ServiceAnaliseDeImagemOut,
    ServiceBuscaPorImagemOut,
    ServiceBuscaPorPlacaOut,
    ServiceBuscaPorRadarOut,
    ServiceCercoEletronicoOut,
    ServiceOutrosOut,
    ServicePlacasConjuntasItemOut,
    ServicePlacasConjuntasOut,
    ServicePlacasCorrelatasItemOut,
    ServicePlacasCorrelatasOut,
    ServiceReservaDeImagemOut,
    TicketAttachmentOut,
    TicketCommentOut,
    TicketCreateFocalPoint,
    TicketCreateIn,
    TicketCreateRequester,
    TicketCreateResultOut,
    TicketDashboardFilterIn,
    TicketDashboardItemOut,
    TicketDashboardOut,
    TicketDashboardSectionOut,
    TicketDashboardServiceTagOut,
    TicketDetection,
    TicketFocalPointSearchOut,
    TicketInternalNumberSearchOut,
    TicketOfficialLetterSearchOut,
    TicketOut,
    TicketProcedureNumberSearchOut,
    TicketRequesterSearchOut,
    TicketSearchOut,
)
from app.modules.tickets.domain.entities import (
    Ticket,
    TicketAttachment,
    TicketComment,
    TicketCorrelatedPlatesService,
    TicketCorrelatedPlatesServiceItem,
    TicketElectronicFenceService,
    TicketFocalPoint,
    TicketImageAnalysisService,
    TicketImageReservationService,
    TicketImageSearchService,
    TicketJointPlatesService,
    TicketJointPlatesServiceItem,
    TicketNature,
    TicketOtherService,
    TicketPlateSearchService,
    TicketRadarSearchService,
    TicketType,
)


MAX_FILE_BYTES = 10 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def parse_ticket_payload(payload: str) -> TicketCreateIn:
    try:
        raw = json.loads(payload)
        return TicketCreateIn.parse_obj(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="payload deve ser um JSON válido.")
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())


async def _read_file_and_validate(file: UploadFile) -> Tuple[bytes, int]:
    content = await file.read()
    size = len(content)

    if size > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Arquivo '{file.filename}' excede 10MB.",
        )

    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo inválido '{file.content_type}' em '{file.filename}'.",
        )

    return content, size


async def _prepare_and_upload_files(
    *,
    ticket_id: str,
    files: List[UploadFile],
) -> List[dict]:
    bucket_name = GCS_BUCKET_NAME
    uploaded_files: List[dict] = []

    try:
        for f in files:
            content, size = await _read_file_and_validate(f)
            object_name = build_ticket_object_name(ticket_id, f.filename)

            meta = await gcs_upload_file_bytes(
                bucket_name=bucket_name,
                object_name=object_name,
                content=content,
                content_type=f.content_type,
            )

            uploaded_files.append(
                {
                    "filename": f.filename,
                    "content_type": f.content_type,
                    "size_bytes": size,
                    "storage_key": object_name,
                    "storage_meta": meta,
                }
            )

        return uploaded_files

    except Exception:
        if uploaded_files:
            await gcs_delete_objects(
                bucket_name=bucket_name,
                object_names=[item["storage_key"] for item in uploaded_files],
            )
        raise


async def _create_ticket_attachments(
    *,
    ticket: Ticket,
    uploaded_files: List[dict],
    connection,
) -> List[TicketAttachmentOut]:
    attachments_out: List[TicketAttachmentOut] = []

    for item in uploaded_files:
        att = await TicketAttachment.create(
            ticket=ticket,
            filename=item["filename"],
            content_type=item["content_type"],
            size_bytes=item["size_bytes"],
            storage_key=item["storage_key"],
            using_db=connection,
        )

        attachments_out.append(
            TicketAttachmentOut(
                id=str(att.id),
                filename=att.filename,
                content_type=att.content_type,
                size_bytes=att.size_bytes,
                created_at=att.created_at,
            )
        )

    return attachments_out


async def _get_parent_ticket_or_raise(parent_ticket_id: Optional[str]) -> Optional[Ticket]:
    if not parent_ticket_id:
        return None

    parent_ticket = await Ticket.get_or_none(id=parent_ticket_id)
    if not parent_ticket:
        raise HTTPException(status_code=400, detail="associar_chamado_id inválido.")

    return parent_ticket


async def _get_ticket_type_or_raise(ticket_type_id: str) -> TicketType:
    ticket_type_obj = await TicketType.get_or_none(id=ticket_type_id)
    if not ticket_type_obj:
        raise HTTPException(
            status_code=400,
            detail="tipo_chamado_id inválido (TicketType não encontrado).",
        )
    return ticket_type_obj


async def _get_nature_or_raise(natureza_id: Optional[str]) -> Optional[TicketNature]:
    if not natureza_id:
        return None

    nature_obj = await TicketNature.get_or_none(id=natureza_id)
    if not nature_obj:
        raise HTTPException(
            status_code=400,
            detail="natureza_id inválido (TicketNature não encontrada).",
        )
    return nature_obj


async def _get_operation_or_raise(operation_id: Optional[str]) -> Optional[Operation]:
    if not operation_id:
        return None

    operation_obj = await Operation.get_or_none(id=operation_id)
    if not operation_obj:
        raise HTTPException(
            status_code=400,
            detail="operation_id inválido (Operation não encontrada).",
        )
    return operation_obj


def _resolve_press_fields(ticket_in: TicketCreateIn) -> Tuple[Optional[str], Optional[str]]:
    if not ticket_in.possui_apelido_imprensa:
        return None, None

    if not ticket_in.apelido_imprensa and not ticket_in.link_materia:
        raise HTTPException(
            status_code=400,
            detail=(
                "Se 'possui_apelido_imprensa' for true, "
                "informe 'apelido_imprensa' e/ou 'link_materia'."
            ),
        )

    return (
        ticket_in.apelido_imprensa,
        str(ticket_in.link_materia) if ticket_in.link_materia else None,
    )


async def _create_ticket_base(
    *,
    ticket_id: str,
    ticket_in: TicketCreateIn,
    ticket_type_obj: TicketType,
    nature_obj: Optional[TicketNature],
    operation_obj: Optional[Operation],
    press_nickname: Optional[str],
    press_link: Optional[str],
    connection,
) -> Ticket:
    return await Ticket.create(
        id=ticket_id,
        parent_ticket_id=ticket_in.associar_chamado_id,
        operation=operation_obj,
        ticket_type=ticket_type_obj,
        procedure_number=ticket_in.numero_procedimento,
        official_letter_number=ticket_in.numero_oficio,
        base_date=ticket_in.data_base,
        nature=nature_obj,
        has_press_nickname=ticket_in.possui_apelido_imprensa,
        press_nickname=press_nickname,
        press_link=press_link,
        requester_name=ticket_in.requisitante.requisitante_nome,
        requester_phone=ticket_in.requisitante.requisitante_telefone,
        requester_email=str(ticket_in.requisitante.requisitante_email)
        if ticket_in.requisitante.requisitante_email
        else None,
        team_id=ticket_in.equipe_id,
        priority=ticket_in.prioridade.value,
        using_db=connection,
    )


async def _create_focal_points(
    *,
    ticket: Ticket,
    pontos_focais: List[TicketCreateFocalPoint],
    connection,
) -> None:
    if not pontos_focais:
        return

    await TicketFocalPoint.bulk_create(
        [
            TicketFocalPoint(
                ticket=ticket,
                name=fp.nome,
                phone=fp.telefone,
                email=str(fp.email) if fp.email else None,
            )
            for fp in pontos_focais
        ],
        using_db=connection,
    )


async def _create_initial_comment(
    *,
    ticket: Ticket,
    author: Optional[User],
    comentario_inicial: Optional[str],
    connection,
) -> None:
    if not comentario_inicial or not comentario_inicial.strip():
        return

    await TicketComment.create(
        ticket=ticket,
        author=author,
        body=comentario_inicial.strip(),
        using_db=connection,
    )


async def _create_plate_search_services(
    *,
    ticket: Ticket,
    services,
    connection,
) -> None:
    if not services:
        return

    await TicketPlateSearchService.bulk_create(
        [
            TicketPlateSearchService(
                ticket=ticket,
                period_start=service.period_start,
                period_end=service.period_end,
                plate=service.plate,
            )
            for service in services
        ],
        using_db=connection,
    )


async def _create_radar_search_services(
    *,
    ticket: Ticket,
    services,
    connection,
) -> None:
    if not services:
        return

    await TicketRadarSearchService.bulk_create(
        [
            TicketRadarSearchService(
                ticket=ticket,
                period_start=service.period_start,
                period_end=service.period_end,
                plate=service.plate,
                radar_address=service.radar_address,
            )
            for service in services
        ],
        using_db=connection,
    )


async def _create_electronic_fence_services(
    *,
    ticket: Ticket,
    services,
    connection,
) -> None:
    if not services:
        return

    await TicketElectronicFenceService.bulk_create(
        [
            TicketElectronicFenceService(
                ticket=ticket,
                plate=service.plate,
                vehicle_observations=service.vehicle_observations,
            )
            for service in services
        ],
        using_db=connection,
    )


async def _create_image_search_services(
    *,
    ticket: Ticket,
    services,
    connection,
) -> None:
    if not services:
        return

    await TicketImageSearchService.bulk_create(
        [
            TicketImageSearchService(
                ticket=ticket,
                period_start=service.period_start,
                period_end=service.period_end,
                plate=service.plate,
                address=service.address,
                description=service.description,
            )
            for service in services
        ],
        using_db=connection,
    )


async def _create_correlated_plate_services(
    *,
    ticket: Ticket,
    services,
    connection,
) -> None:
    if not services:
        return

    for service_in in services:
        service = await TicketCorrelatedPlatesService.create(
            ticket=ticket,
            interest_interval_minutes=service_in.interest_interval_minutes,
            detection_count=service_in.detection_count,
            detection=service_in.detection.value if service_in.detection else None,
            using_db=connection,
        )

        if service_in.items:
            await TicketCorrelatedPlatesServiceItem.bulk_create(
                [
                    TicketCorrelatedPlatesServiceItem(
                        service=service,
                        period_start=item.period_start,
                        period_end=item.period_end,
                        plate=item.plate,
                    )
                    for item in service_in.items
                ],
                using_db=connection,
            )


async def _create_joint_plate_services(
    *,
    ticket: Ticket,
    services,
    connection,
) -> None:
    if not services:
        return

    for service_in in services:
        service = await TicketJointPlatesService.create(
            ticket=ticket,
            interest_interval_minutes=service_in.interest_interval_minutes,
            detection_count=service_in.detection_count,
            detection=service_in.detection.value if service_in.detection else None,
            using_db=connection,
        )

        if service_in.items:
            await TicketJointPlatesServiceItem.bulk_create(
                [
                    TicketJointPlatesServiceItem(
                        service=service,
                        period_start=item.period_start,
                        period_end=item.period_end,
                        plate=item.plate,
                    )
                    for item in service_in.items
                ],
                using_db=connection,
            )


async def _create_image_reservation_services(
    *,
    ticket: Ticket,
    services,
    connection,
) -> None:
    if not services:
        return

    await TicketImageReservationService.bulk_create(
        [
            TicketImageReservationService(
                ticket=ticket,
                period_start=service.period_start,
                period_end=service.period_end,
                orientation=service.orientation,
            )
            for service in services
        ],
        using_db=connection,
    )


async def _create_image_analysis_services(
    *,
    ticket: Ticket,
    services,
    connection,
) -> None:
    if not services:
        return

    await TicketImageAnalysisService.bulk_create(
        [
            TicketImageAnalysisService(
                ticket=ticket,
                period_start=service.period_start,
                period_end=service.period_end,
                orientation=service.orientation,
            )
            for service in services
        ],
        using_db=connection,
    )


async def _create_other_services(
    *,
    ticket: Ticket,
    services,
    connection,
) -> None:
    if not services:
        return

    await TicketOtherService.bulk_create(
        [
            TicketOtherService(
                ticket=ticket,
                orientation=service.orientation,
            )
            for service in services
        ],
        using_db=connection,
    )


async def _create_ticket_related_data(
    *,
    ticket: Ticket,
    ticket_in: TicketCreateIn,
    author: Optional[User],
    uploaded_files: List[dict],
    connection,
) -> None:
    await _create_focal_points(
        ticket=ticket,
        pontos_focais=ticket_in.pontos_focais,
        connection=connection,
    )

    await _create_initial_comment(
        ticket=ticket,
        author=author,
        comentario_inicial=ticket_in.comentario_inicial,
        connection=connection,
    )

    await _create_plate_search_services(
        ticket=ticket,
        services=ticket_in.busca_por_placa,
        connection=connection,
    )

    await _create_radar_search_services(
        ticket=ticket,
        services=ticket_in.busca_por_radar,
        connection=connection,
    )

    await _create_electronic_fence_services(
        ticket=ticket,
        services=ticket_in.cerco_eletronico,
        connection=connection,
    )

    await _create_image_search_services(
        ticket=ticket,
        services=ticket_in.busca_por_imagem,
        connection=connection,
    )

    await _create_correlated_plate_services(
        ticket=ticket,
        services=ticket_in.placas_correlatas,
        connection=connection,
    )

    await _create_joint_plate_services(
        ticket=ticket,
        services=ticket_in.placas_conjuntas,
        connection=connection,
    )

    await _create_image_reservation_services(
        ticket=ticket,
        services=ticket_in.reserva_de_imagem,
        connection=connection,
    )

    await _create_image_analysis_services(
        ticket=ticket,
        services=ticket_in.analise_de_imagem,
        connection=connection,
    )

    await _create_other_services(
        ticket=ticket,
        services=ticket_in.outros,
        connection=connection,
    )

    await _create_ticket_attachments(
        ticket=ticket,
        uploaded_files=uploaded_files,
        connection=connection,
    )


async def create_ticket(
    *,
    ticket_in: TicketCreateIn,
    author: Optional[User],
    files: Optional[List[UploadFile]] = None,
) -> TicketCreateResultOut:
    await _get_parent_ticket_or_raise(ticket_in.associar_chamado_id)
    ticket_type_obj = await _get_ticket_type_or_raise(ticket_in.tipo_chamado_id)
    nature_obj = await _get_nature_or_raise(ticket_in.natureza_id)
    operation_obj = await _get_operation_or_raise(ticket_in.operation_id)
    press_nickname, press_link = _resolve_press_fields(ticket_in)

    ticket_id = str(uuid.uuid4())
    uploaded_files: List[dict] = []

    if files:
        uploaded_files = await _prepare_and_upload_files(
            ticket_id=ticket_id,
            files=files,
        )

    try:
        async with in_transaction() as connection:
            ticket = await _create_ticket_base(
                ticket_id=ticket_id,
                ticket_in=ticket_in,
                ticket_type_obj=ticket_type_obj,
                nature_obj=nature_obj,
                operation_obj=operation_obj,
                press_nickname=press_nickname,
                press_link=press_link,
                connection=connection,
            )

            await _create_ticket_related_data(
                ticket=ticket,
                ticket_in=ticket_in,
                author=author,
                uploaded_files=uploaded_files,
                connection=connection,
            )

    except Exception as exc:
        if uploaded_files:
            logger.warning(
                f"Falha após upload para GCS. Iniciando compensação manual. "
                f"ticket_id='{ticket_id}', error='{exc}'"
            )
            await gcs_delete_objects(
                bucket_name=GCS_BUCKET_NAME,
                object_names=[item["storage_key"] for item in uploaded_files],
            )
        raise

    return TicketCreateResultOut(id=ticket_id)


async def get_ticket_by_id(*, ticket_id: str) -> TicketOut:
    ticket = (
        await Ticket.filter(id=ticket_id)
        .prefetch_related(
            "operation",
            "ticket_type",
            "nature",
            "parent_ticket",
            "focal_points",
            "comments__author",
            "attachments",
            "plate_search_services",
            "radar_search_services",
            "electronic_fence_services",
            "image_search_services",
            "correlated_plate_services__items",
            "joint_plate_services__items",
            "image_reservation_services",
            "image_analysis_services",
            "other_services",
        )
        .first()
    )

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não encontrado.")

    focal_points = sorted(ticket.focal_points, key=lambda x: x.created_at)
    comments = sorted(ticket.comments, key=lambda x: x.created_at)
    attachments = sorted(ticket.attachments, key=lambda x: x.created_at)

    busca_por_placa = sorted(ticket.plate_search_services, key=lambda x: x.created_at)
    busca_por_radar = sorted(ticket.radar_search_services, key=lambda x: x.created_at)
    cerco_eletronico = sorted(ticket.electronic_fence_services, key=lambda x: x.created_at)
    busca_por_imagem = sorted(ticket.image_search_services, key=lambda x: x.created_at)

    placas_correlatas = sorted(ticket.correlated_plate_services, key=lambda x: x.created_at)
    placas_conjuntas = sorted(ticket.joint_plate_services, key=lambda x: x.created_at)

    reserva_de_imagem = sorted(ticket.image_reservation_services, key=lambda x: x.created_at)
    analise_de_imagem = sorted(ticket.image_analysis_services, key=lambda x: x.created_at)
    outros = sorted(ticket.other_services, key=lambda x: x.created_at)

    return TicketOut(
        id=str(ticket.id),
        criado_em=ticket.created_at,
        associar_chamado_id=str(ticket.parent_ticket_id) if ticket.parent_ticket_id else None,
        tipo_chamado_id=str(ticket.ticket_type_id),
        operation_id=str(ticket.operation_id) if ticket.operation_id else None,
        numero_procedimento=ticket.procedure_number,
        numero_oficio=ticket.official_letter_number,
        data_base=ticket.base_date,
        natureza_id=str(ticket.nature_id) if ticket.nature_id else None,
        possui_apelido_imprensa=ticket.has_press_nickname,
        apelido_imprensa=ticket.press_nickname,
        link_materia=ticket.press_link,
        requisitante=TicketCreateRequester(
            requisitante_nome=ticket.requester_name,
            requisitante_telefone=ticket.requester_phone,
            requisitante_email=ticket.requester_email,
        ),
        pontos_focais=[
            TicketCreateFocalPoint(
                nome=fp.name,
                telefone=fp.phone,
                email=fp.email,
            )
            for fp in focal_points
        ],
        equipe_id=ticket.team_id,
        prioridade=TicketPriority(ticket.priority),
        comentarios=[
            TicketCommentOut(
                id=str(comment.id),
                created_at=comment.created_at,
                author_id=str(comment.author_id) if comment.author_id else None,
                body=comment.body,
            )
            for comment in comments
        ],
        anexos=[
            TicketAttachmentOut(
                id=str(attachment.id),
                filename=attachment.filename,
                content_type=attachment.content_type,
                size_bytes=attachment.size_bytes,
                created_at=attachment.created_at,
            )
            for attachment in attachments
        ],
        busca_por_placa=[
            ServiceBuscaPorPlacaOut(
                id=str(service.id),
                created_at=service.created_at,
                period_start=service.period_start,
                period_end=service.period_end,
                plate=service.plate,
            )
            for service in busca_por_placa
        ],
        busca_por_radar=[
            ServiceBuscaPorRadarOut(
                id=str(service.id),
                created_at=service.created_at,
                period_start=service.period_start,
                period_end=service.period_end,
                plate=service.plate,
                radar_address=service.radar_address,
            )
            for service in busca_por_radar
        ],
        cerco_eletronico=[
            ServiceCercoEletronicoOut(
                id=str(service.id),
                created_at=service.created_at,
                plate=service.plate,
                vehicle_observations=service.vehicle_observations,
            )
            for service in cerco_eletronico
        ],
        busca_por_imagem=[
            ServiceBuscaPorImagemOut(
                id=str(service.id),
                created_at=service.created_at,
                period_start=service.period_start,
                period_end=service.period_end,
                plate=service.plate,
                address=service.address,
                description=service.description,
            )
            for service in busca_por_imagem
        ],
        placas_correlatas=[
            ServicePlacasCorrelatasOut(
                id=str(service.id),
                created_at=service.created_at,
                interest_interval_minutes=service.interest_interval_minutes,
                detection_count=service.detection_count,
                detection=TicketDetection(service.detection) if service.detection else None,
                items=[
                    ServicePlacasCorrelatasItemOut(
                        id=str(item.id),
                        created_at=item.created_at,
                        period_start=item.period_start,
                        period_end=item.period_end,
                        plate=item.plate,
                    )
                    for item in sorted(service.items, key=lambda x: x.created_at)
                ],
            )
            for service in placas_correlatas
        ],
        placas_conjuntas=[
            ServicePlacasConjuntasOut(
                id=str(service.id),
                created_at=service.created_at,
                interest_interval_minutes=service.interest_interval_minutes,
                detection_count=service.detection_count,
                detection=TicketDetection(service.detection) if service.detection else None,
                items=[
                    ServicePlacasConjuntasItemOut(
                        id=str(item.id),
                        created_at=item.created_at,
                        period_start=item.period_start,
                        period_end=item.period_end,
                        plate=item.plate,
                    )
                    for item in sorted(service.items, key=lambda x: x.created_at)
                ],
            )
            for service in placas_conjuntas
        ],
        reserva_de_imagem=[
            ServiceReservaDeImagemOut(
                id=str(service.id),
                created_at=service.created_at,
                period_start=service.period_start,
                period_end=service.period_end,
                orientation=service.orientation,
            )
            for service in reserva_de_imagem
        ],
        analise_de_imagem=[
            ServiceAnaliseDeImagemOut(
                id=str(service.id),
                created_at=service.created_at,
                period_start=service.period_start,
                period_end=service.period_end,
                orientation=service.orientation,
            )
            for service in analise_de_imagem
        ],
        outros=[
            ServiceOutrosOut(
                id=str(service.id),
                created_at=service.created_at,
                orientation=service.orientation,
            )
            for service in outros
        ],
    )


async def search_tickets(*, search: str) -> List[TicketSearchOut]:
    termo = (search or "").strip()

    if not termo:
        return []

    tickets = (
        await Ticket.filter(
            Q(procedure_number__icontains=termo)
            | Q(official_letter_number__icontains=termo)
            | Q(requester_name__icontains=termo)
        )
        .order_by("-created_at")
        .limit(20)
    )

    return [
        TicketSearchOut(
            id=str(ticket.id),
            criado_em=ticket.created_at,
            titulo=build_ticket_search_label(ticket),
        )
        for ticket in tickets
    ]


def build_ticket_search_label(ticket: "Ticket") -> str:
    partes: list[str] = []

    if ticket.base_date:
        partes.append(f"Chamado {ticket.base_date.strftime('%d/%m/%Y')}")

    if ticket.procedure_number:
        partes.append(f"Proc. {ticket.procedure_number}")

    if ticket.official_letter_number:
        partes.append(f"Ofício {ticket.official_letter_number}")

    if ticket.requester_name:
        partes.append(f"Req. {ticket.requester_name}")

    return " • ".join(partes)


def _build_dashboard_service_labels(ticket: Ticket) -> List[str]:
    labels: List[str] = []

    service_map = [
        ("plate_search_services", "busca de placa"),
        ("radar_search_services", "busca de radar"),
        ("electronic_fence_services", "cerco"),
        ("image_search_services", "busca de imagem"),
        ("correlated_plate_services", "placas correlatas"),
        ("joint_plate_services", "placas conjuntas"),
        ("image_reservation_services", "reserva de imagem"),
        ("image_analysis_services", "análise de imagem"),
        ("other_services", "outros"),
    ]

    for attr_name, label in service_map:
        rows = getattr(ticket, attr_name, []) or []
        for _ in rows:
            labels.append(label)

    return labels

async def get_tickets_dashboard(
    *,
    user: User,
    filters: TicketDashboardFilterIn,
) -> TicketDashboardOut:
    period_days = max(filters.period_days, 1)
    overdue_after_days = max(filters.overdue_after_days, 1)

    has_explicit_data_entrada_filter = (
        filters.data_entrada_inicio is not None
        or filters.data_entrada_fim is not None
    )

    if not has_explicit_data_entrada_filter:
        now_utc = datetime.now(timezone.utc)
        date_from = now_utc - timedelta(days=period_days)
        query = Ticket.filter(created_at__gte=date_from)
    else:
        query = Ticket.all()

    termo = (filters.search or "").strip()
    if termo:
        search_q = (
            Q(requester_name__icontains=termo)
            | Q(operation__title__icontains=termo)
            | Q(procedure_number__icontains=termo)
            | Q(official_letter_number__icontains=termo)
            | Q(focal_points__name__icontains=termo)
        )

        if termo.isdigit():
            search_q = search_q | Q(internal_number=int(termo))

        query = query.filter(search_q)

    if filters.tipo_chamado_id:
        query = query.filter(ticket_type_id__in=filters.tipo_chamado_id)

    if filters.numero_interno:
        query = query.filter(internal_number__in=filters.numero_interno)

    if filters.numero_procedimento:
        q = Q()
        for item in filters.numero_procedimento:
            value = (item or "").strip()
            if value:
                q |= Q(procedure_number__icontains=value)
        query = query.filter(q)

    if filters.numero_oficio:
        q = Q()
        for item in filters.numero_oficio:
            value = (item or "").strip()
            if value:
                q |= Q(official_letter_number__icontains=value)
        query = query.filter(q)

    if filters.natureza_id:
        query = query.filter(nature_id__in=filters.natureza_id)

    if filters.demandante_id:
        query = query.filter(operation_id__in=filters.demandante_id)

    if filters.requisitante:
        q = Q()
        for item in filters.requisitante:
            value = (item or "").strip()
            if value:
                q |= Q(requester_name__icontains=value)
        query = query.filter(q)

    if filters.ponto_focal:
        q = Q()
        for item in filters.ponto_focal:
            value = (item or "").strip()
            if value:
                q |= Q(focal_points__name__icontains=value)
        query = query.filter(q)

    if filters.data_base_inicio:
        query = query.filter(base_date__gte=filters.data_base_inicio)

    if filters.data_base_fim:
        query = query.filter(base_date__lte=filters.data_base_fim)

    if filters.data_entrada_inicio:
        dt_inicio = datetime.combine(filters.data_entrada_inicio, time.min)
        query = query.filter(created_at__gte=dt_inicio)

    if filters.data_entrada_fim:
        dt_fim = datetime.combine(filters.data_entrada_fim, time.max)
        query = query.filter(created_at__lte=dt_fim)

    if filters.status:
        status_validos = [item for item in filters.status if item]
        if status_validos:
            query = query.filter(status__in=status_validos)

    if filters.prioridade:
        prioridades_validas = [item for item in filters.prioridade if item]
        if prioridades_validas:
            query = query.filter(priority__in=prioridades_validas)

    if filters.equipe:
        equipes_validas = [item for item in filters.equipe if item]
        if equipes_validas:
            query = query.filter(team_id__in=equipes_validas)

    services_q = _build_services_filter_q(filters.servicos_realizados)
    if services_q:
        query = query.filter(services_q)

    query = query.distinct()

    total = await query.count()

    tickets = await (
        query.prefetch_related(
            "operation",
            "team",
            "ticket_type",
            "nature",
            "focal_points",
            "plate_search_services",
            "radar_search_services",
            "electronic_fence_services",
            "image_search_services",
            "correlated_plate_services",
            "joint_plate_services",
            "image_reservation_services",
            "image_analysis_services",
            "other_services",
        )
        .order_by("-created_at")
    )

    pendentes_items = []
    restritos_items = []
    aguardando_revisao_items = []
    bloqueados_items = []
    urgentes_items = []
    em_atraso_items = []

    concluidos_total = 0

    for ticket in tickets:
        status_ticket = TicketStatus(ticket.status)
        priority = TicketPriority(ticket.priority)

        created_at = ticket.created_at
        current_time = (
            datetime.now(created_at.tzinfo)
            if created_at.tzinfo is not None
            else datetime.now(timezone.utc)
        )

        aging_days = max((current_time - created_at).days, 0)
        service_labels = _build_dashboard_service_labels(ticket)

        item = TicketDashboardItemOut(
            id=str(ticket.id),
            numero_interno=ticket.internal_number,
            chamado=str(ticket.internal_number).zfill(7),
            status=status_ticket.value,
            demandante=ticket.operation.title if ticket.operation else "",
            equipe=ticket.team.name if ticket.team else "",
            responsavel=ticket.operation.title if ticket.operation else "",
            prioridade=priority.value,
            dias_atraso=aging_days,
            servicos=[
                TicketDashboardServiceTagOut(label=label)
                for label in service_labels
            ],
        )

        if status_ticket == TicketStatus.CONCLUIDO:
            concluidos_total += 1

        if status_ticket == TicketStatus.PENDENTE:
            pendentes_items.append(item)
        elif status_ticket == TicketStatus.RESTRITO:
            restritos_items.append(item)
        elif status_ticket == TicketStatus.AGUARDANDO_REVISAO:
            aguardando_revisao_items.append(item)
        elif status_ticket == TicketStatus.BLOQUEADO:
            bloqueados_items.append(item)

        if priority == TicketPriority.URGENTE:
            urgentes_items.append(item)

        if status_ticket != TicketStatus.CONCLUIDO and aging_days > overdue_after_days:
            em_atraso_items.append(item)

    return TicketDashboardOut(
        pendentes=TicketDashboardSectionOut(
            total=len(pendentes_items),
            items=pendentes_items,
        ),
        restritos=TicketDashboardSectionOut(
            total=len(restritos_items),
            items=restritos_items,
        ),
        aguardando_revisao=TicketDashboardSectionOut(
            total=len(aguardando_revisao_items),
            items=aguardando_revisao_items,
        ),
        bloqueados=TicketDashboardSectionOut(
            total=len(bloqueados_items),
            items=bloqueados_items,
        ),
        concluidos_total=concluidos_total,
        urgentes=TicketDashboardSectionOut(
            total=len(urgentes_items),
            items=urgentes_items,
        ),
        em_atraso=TicketDashboardSectionOut(
            total=len(em_atraso_items),
            items=em_atraso_items,
        ),
        total=total,
        period_days=period_days,
        overdue_after_days=overdue_after_days,
    )


async def search_official_letters(*, search: str) -> List[TicketOfficialLetterSearchOut]:
    termo = (search or "").strip()

    if len(termo) < 2:
        raise HTTPException(
            status_code=400,
            detail="O parâmetro 'search' deve ter no mínimo 2 caracteres.",
        )

    rows = (
        await Ticket.filter(
            official_letter_number__isnull=False,
            official_letter_number__icontains=termo,
        )
        .exclude(official_letter_number="")
        .distinct()
        .order_by("official_letter_number")
        .limit(20)
        .values_list("official_letter_number", flat=True)
    )

    return [
        TicketOfficialLetterSearchOut(numero_oficio=numero)
        for numero in rows
        if numero
    ]

async def search_internal_numbers(*, search: str) -> List[TicketInternalNumberSearchOut]:
    termo = (search or "").strip()

    if len(termo) < 2:
        raise HTTPException(
            status_code=400,
            detail="O parâmetro 'search' deve ter no mínimo 2 caracteres.",
        )

    rows = (
        await Ticket.filter(
            internal_number__icontains=termo
        )
        .order_by("-created_at")
        .limit(20)
        .values_list("internal_number", flat=True)
    )

    return [
        TicketInternalNumberSearchOut(numero_interno=num)
        for num in rows
    ]

async def search_procedure_numbers(*, search: str) -> List[TicketProcedureNumberSearchOut]:
    termo = (search or "").strip()

    if len(termo) < 2:
        raise HTTPException(
            status_code=400,
            detail="O parâmetro 'search' deve ter no mínimo 2 caracteres.",
        )

    rows = (
        await Ticket.filter(
            procedure_number__isnull=False,
            procedure_number__icontains=termo,
        )
        .exclude(procedure_number="")
        .distinct()
        .order_by("procedure_number")
        .limit(20)
        .values_list("procedure_number", flat=True)
    )

    return [
        TicketProcedureNumberSearchOut(numero_procedimento=num)
        for num in rows
        if num
    ]


async def search_requesters(*, search: str) -> List[TicketRequesterSearchOut]:
    termo = (search or "").strip()

    if len(termo) < 2:
        raise HTTPException(
            status_code=400,
            detail="O parâmetro 'search' deve ter no mínimo 2 caracteres.",
        )

    rows = (
        await Ticket.filter(
            requester_name__icontains=termo
        )
        .distinct()
        .order_by("requester_name")
        .limit(20)
        .values_list("requester_name", flat=True)
    )

    return [
        TicketRequesterSearchOut(requisitante=name)
        for name in rows
        if name
    ]

async def search_focal_points(*, search: str) -> List[TicketFocalPointSearchOut]:
    termo = (search or "").strip()

    if len(termo) < 2:
        raise HTTPException(
            status_code=400,
            detail="O parâmetro 'search' deve ter no mínimo 2 caracteres.",
        )

    rows = (
        await TicketFocalPoint.filter(
            name__icontains=termo
        )
        .distinct()
        .order_by("name")
        .limit(20)
        .values_list("name", flat=True)
    )

    return [
        TicketFocalPointSearchOut(ponto_focal=name)
        for name in rows
        if name
    ]


def _normalize_dashboard_service_filter(value: str) -> Optional[str]:
    if not value:
        return None

    normalized = (
        value.strip()
        .lower()
        .replace("ç", "c")
        .replace("á", "a")
        .replace("à", "a")
        .replace("ã", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
    )

    mapping = {
        "busca por placa": "plate_search_services",
        "busca de placa": "plate_search_services",
        "busca por radar": "radar_search_services",
        "busca de radar": "radar_search_services",
        "cerco eletronico": "electronic_fence_services",
        "cerco": "electronic_fence_services",
        "busca por imagem": "image_search_services",
        "busca de imagem": "image_search_services",
        "placa correlatas": "correlated_plate_services",
        "placas correlatas": "correlated_plate_services",
        "placas conjuntas": "joint_plate_services",
        "reserva de imagem": "image_reservation_services",
        "analise de imagem": "image_analysis_services",
        "análise de imagem": "image_analysis_services",
        "outros": "other_services",
    }

    return mapping.get(normalized)


def _build_services_filter_q(servicos_realizados: Optional[List[str]]) -> Optional[Q]:
    if not servicos_realizados:
        return None

    service_relation_map = {
        "plate_search_services": Q(plate_search_services__id__not_isnull=True),
        "radar_search_services": Q(radar_search_services__id__not_isnull=True),
        "electronic_fence_services": Q(electronic_fence_services__id__not_isnull=True),
        "image_search_services": Q(image_search_services__id__not_isnull=True),
        "correlated_plate_services": Q(correlated_plate_services__id__not_isnull=True),
        "joint_plate_services": Q(joint_plate_services__id__not_isnull=True),
        "image_reservation_services": Q(image_reservation_services__id__not_isnull=True),
        "image_analysis_services": Q(image_analysis_services__id__not_isnull=True),
        "other_services": Q(other_services__id__not_isnull=True),
    }

    q_objects: List[Q] = []

    for raw_value in servicos_realizados:
        normalized_key = _normalize_dashboard_service_filter(raw_value)
        if normalized_key and normalized_key in service_relation_map:
            q_objects.append(service_relation_map[normalized_key])

    if not q_objects:
        return None

    combined_q = q_objects[0]
    for q_obj in q_objects[1:]:
        combined_q = combined_q | q_obj

    return combined_q