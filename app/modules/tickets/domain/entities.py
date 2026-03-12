# -*- coding: utf-8 -*-

from app.modules.tickets.domain.enum import TicketPriority, TicketStatus
from tortoise import fields
from tortoise.models import Model


class TicketType(Model):
    id = fields.UUIDField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    name = fields.CharField(max_length=80, unique=True)
    description = fields.TextField(null=True)
    is_active = fields.BooleanField(default=True)

    class Meta:
        table = "ticket_types"


class TicketNature(Model):
    id = fields.UUIDField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    name = fields.CharField(max_length=40, unique=True)
    description = fields.TextField(null=True)
    is_active = fields.BooleanField(default=True)

    class Meta:
        table = "ticket_natures"


class Ticket(Model):
    id = fields.UUIDField(pk=True)
    internal_number = fields.IntField(generated=True, unique=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    status = fields.CharEnumField(
        TicketStatus,
        max_length=30,
        default=TicketStatus.PENDENTE
    )

    priority = fields.CharEnumField(
        TicketPriority,
        max_length=30,
    )


    parent_ticket = fields.ForeignKeyField(
        "app.Ticket",
        related_name="children",
        null=True,
        on_delete=fields.SET_NULL,
    )

    operation = fields.ForeignKeyField(
        "app.Operation",
        related_name="tickets",
        null=False,
        on_delete=fields.RESTRICT,
    )

    ticket_type = fields.ForeignKeyField(
        "app.TicketType",
        related_name="tickets",
        null=False,
        on_delete=fields.RESTRICT,
    )

    procedure_number = fields.CharField(max_length=60, null=True)
    official_letter_number = fields.CharField(max_length=60, null=True)
    base_date = fields.DateField(null=True)

    nature = fields.ForeignKeyField(
        "app.TicketNature",
        related_name="tickets",
        null=True,
        on_delete=fields.SET_NULL,
    )

    has_press_nickname = fields.BooleanField(default=False)
    press_nickname = fields.CharField(max_length=120, null=True)
    press_link = fields.CharField(max_length=500, null=True)

    requester_name = fields.CharField(max_length=120)
    requester_phone = fields.CharField(max_length=30, null=True)
    requester_email = fields.CharField(max_length=254)

    team_id = fields.CharField(max_length=80, null=True)

    class Meta:
        table = "tickets"


class TicketFocalPoint(Model):
    id = fields.UUIDField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    ticket = fields.ForeignKeyField(
        "app.Ticket",
        related_name="focal_points",
        on_delete=fields.CASCADE,
    )

    name = fields.CharField(max_length=120)
    phone = fields.CharField(max_length=30, null=True)
    email = fields.CharField(max_length=254, null=True)

    class Meta:
        table = "ticket_focal_points"
        indexes = (("ticket_id", "created_at"),)


class TicketComment(Model):
    id = fields.UUIDField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    ticket = fields.ForeignKeyField(
        "app.Ticket",
        related_name="comments",
        on_delete=fields.CASCADE,
    )

    author = fields.ForeignKeyField(
        "app.User",
        related_name="ticket_comments",
        null=True,
        on_delete=fields.SET_NULL,
    )

    body = fields.TextField()

    class Meta:
        table = "ticket_comments"


class TicketAttachment(Model):
    id = fields.UUIDField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    ticket = fields.ForeignKeyField(
        "app.Ticket",
        related_name="attachments",
        on_delete=fields.CASCADE,
    )

    filename = fields.CharField(max_length=255)
    content_type = fields.CharField(max_length=120, null=True)
    size_bytes = fields.IntField()
    storage_key = fields.CharField(max_length=500)

    class Meta:
        table = "ticket_attachments"


class TicketPlateSearchService(Model):
    id = fields.UUIDField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    ticket = fields.ForeignKeyField(
        "app.Ticket",
        related_name="plate_search_services",
        on_delete=fields.CASCADE,
    )

    period_start = fields.DatetimeField(null=True)
    period_end = fields.DatetimeField(null=True)
    plate = fields.CharField(max_length=20)

    class Meta:
        table = "ticket_plate_search_services"
        indexes = (("ticket_id", "created_at"),)


class TicketRadarSearchService(Model):
    id = fields.UUIDField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    ticket = fields.ForeignKeyField(
        "app.Ticket",
        related_name="radar_search_services",
        on_delete=fields.CASCADE,
    )

    period_start = fields.DatetimeField(null=True)
    period_end = fields.DatetimeField(null=True)
    plate = fields.CharField(max_length=20)
    radar_address = fields.TextField(null=True)

    class Meta:
        table = "ticket_radar_search_services"
        indexes = (("ticket_id", "created_at"),)


class TicketElectronicFenceService(Model):
    id = fields.UUIDField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    ticket = fields.ForeignKeyField(
        "app.Ticket",
        related_name="electronic_fence_services",
        on_delete=fields.CASCADE,
    )

    plate = fields.CharField(max_length=20)
    vehicle_observations = fields.TextField(null=True)

    class Meta:
        table = "ticket_electronic_fence_services"
        indexes = (("ticket_id", "created_at"),)


class TicketImageSearchService(Model):
    id = fields.UUIDField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    ticket = fields.ForeignKeyField(
        "app.Ticket",
        related_name="image_search_services",
        on_delete=fields.CASCADE,
    )

    period_start = fields.DatetimeField(null=True)
    period_end = fields.DatetimeField(null=True)

    plate = fields.CharField(max_length=20, null=True)
    address = fields.TextField(null=True)
    description = fields.TextField(null=True)

    class Meta:
        table = "ticket_image_search_services"
        indexes = (("ticket_id", "created_at"),)


class TicketCorrelatedPlatesService(Model):
    id = fields.UUIDField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    ticket = fields.ForeignKeyField(
        "app.Ticket",
        related_name="correlated_plate_services",
        on_delete=fields.CASCADE,
    )

    interest_interval_minutes = fields.IntField(null=True)
    detection_count = fields.IntField(null=True)
    detection = fields.CharField(max_length=10, null=True)

    class Meta:
        table = "ticket_correlated_plate_services"
        indexes = (("ticket_id", "created_at"),)


class TicketCorrelatedPlatesServiceItem(Model):
    id = fields.UUIDField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    service = fields.ForeignKeyField(
        "app.TicketCorrelatedPlatesService",
        related_name="items",
        on_delete=fields.CASCADE,
    )

    period_start = fields.DatetimeField(null=True)
    period_end = fields.DatetimeField(null=True)
    plate = fields.CharField(max_length=20)

    class Meta:
        table = "ticket_correlated_plate_service_items"
        indexes = (("service_id", "created_at"),)


class TicketJointPlatesService(Model):
    id = fields.UUIDField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    ticket = fields.ForeignKeyField(
        "app.Ticket",
        related_name="joint_plate_services",
        on_delete=fields.CASCADE,
    )

    interest_interval_minutes = fields.IntField(null=True)
    detection_count = fields.IntField(null=True)
    detection = fields.CharField(max_length=10, null=True)

    class Meta:
        table = "ticket_joint_plate_services"
        indexes = (("ticket_id", "created_at"),)


class TicketJointPlatesServiceItem(Model):
    id = fields.UUIDField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    service = fields.ForeignKeyField(
        "app.TicketJointPlatesService",
        related_name="items",
        on_delete=fields.CASCADE,
    )

    period_start = fields.DatetimeField(null=True)
    period_end = fields.DatetimeField(null=True)
    plate = fields.CharField(max_length=20)

    class Meta:
        table = "ticket_joint_plate_service_items"
        indexes = (("service_id", "created_at"),)


class TicketImageReservationService(Model):
    id = fields.UUIDField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    ticket = fields.ForeignKeyField(
        "app.Ticket",
        related_name="image_reservation_services",
        on_delete=fields.CASCADE,
    )

    period_start = fields.DatetimeField(null=True)
    period_end = fields.DatetimeField(null=True)
    orientation = fields.TextField(null=True)

    class Meta:
        table = "ticket_image_reservation_services"
        indexes = (("ticket_id", "created_at"),)


class TicketImageAnalysisService(Model):
    id = fields.UUIDField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    ticket = fields.ForeignKeyField(
        "app.Ticket",
        related_name="image_analysis_services",
        on_delete=fields.CASCADE,
    )

    period_start = fields.DatetimeField(null=True)
    period_end = fields.DatetimeField(null=True)
    orientation = fields.TextField(null=True)

    class Meta:
        table = "ticket_image_analysis_services"
        indexes = (("ticket_id", "created_at"),)


class TicketOtherService(Model):
    id = fields.UUIDField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    ticket = fields.ForeignKeyField(
        "app.Ticket",
        related_name="other_services",
        on_delete=fields.CASCADE,
    )

    orientation = fields.TextField(null=True)

    class Meta:
        table = "ticket_other_services"
        indexes = (("ticket_id", "created_at"),)