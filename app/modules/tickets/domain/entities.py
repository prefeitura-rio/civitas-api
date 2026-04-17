# -*- coding: utf-8 -*-

from app.modules.tickets.domain.enum import EmailStatus, TicketPriority, TicketStatus, UserRoleEnum
from tortoise import fields
from tortoise.models import Model



class Email(Model):

    id = fields.UUIDField(pk=True)
    message_id = fields.CharField(max_length=255, unique=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    thread_id = fields.CharField(max_length=255, null=True, index=True)

    from_address = fields.CharField(max_length=500, null=True)
    from_name = fields.CharField(max_length=255, null=True)
    to_address = fields.CharField(max_length=500, null=True)
    subject = fields.CharField(max_length=1000, null=True)

    snippet = fields.TextField(null=True)
    body_preview = fields.TextField(null=True)

    date = fields.DatetimeField(null=True)
    internal_date = fields.BigIntField(null=True)

    has_attachments = fields.BooleanField(default=False)
    label_ids = fields.TextField(null=True)

    status = fields.CharEnumField(
        EmailStatus,
        max_length=30,
        default=EmailStatus.NAO_LIDO
    )

    attachments: fields.ReverseRelation["EmailAttachment"]
    tickets: fields.ManyToManyRelation["Ticket"]

    class Meta:
        table = "emails"


class EmailSyncState(Model):
    """Singleton (pk=1): marca d'água explícita do sync Gmail → banco."""

    id = fields.IntField(pk=True)
    watermark_internal_date_ms = fields.BigIntField(null=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "email_sync_state"


class EmailTemplate(Model):

    id = fields.UUIDField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    title = fields.CharField(max_length=255, unique=True, index=True)
    body_html = fields.TextField()
    is_active = fields.BooleanField(default=True)

    class Meta:
        table = "email_templates"


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
        null=True,
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

    procedure_operation = fields.ForeignKeyField(
        "app.Operation",
        related_name="procedure_operation_tickets",
        null=True,
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

    emails: fields.ManyToManyRelation[Email] = fields.ManyToManyField(
        "app.Email",
        related_name="tickets",
        through="ticket_emails",
        forward_key="email_id",
        backward_key="ticket_id",
    )

    has_press_nickname = fields.BooleanField(default=False)
    press_nickname = fields.CharField(max_length=120, null=True)
    press_link = fields.CharField(max_length=500, null=True)

    has_correspondence_address = fields.BooleanField(default=False)
    correspondence_neighborhood = fields.CharField(max_length=120, null=True)
    correspondence_street = fields.CharField(max_length=255, null=True)
    correspondence_number = fields.CharField(max_length=20, null=True)

    requester_name = fields.CharField(max_length=120)
    requester_phone = fields.CharField(max_length=30, null=True)
    requester_email = fields.CharField(max_length=254)

    team = fields.ForeignKeyField(
        "app.Team",
        related_name="tickets",
        null=True,
        on_delete=fields.SET_NULL,
    )

    responsible = fields.ForeignKeyField(
        "app.User",
        related_name="responsible_tickets",
        null=True,
        on_delete=fields.SET_NULL,
    )

    class Meta:
        table = "tickets"

class TicketHistory(Model):
    id = fields.UUIDField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    ticket = fields.ForeignKeyField(
        "app.Ticket",
        related_name="histories",
        on_delete=fields.CASCADE,
    )

    user = fields.ForeignKeyField(
        "app.User",
        related_name="ticket_histories",
        on_delete=fields.CASCADE,
    )

    action = fields.CharField(max_length=100)

    class Meta:
        table = "ticket_histories"
        indexes = (
            ("ticket_id", "created_at"),
            ("user_id", "created_at"),
        )



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

    class Meta:
        table = "ticket_plate_search_services"
        indexes = (("ticket_id", "created_at"),)


class TicketPlateSearchServicePlate(Model):
    id = fields.UUIDField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    service = fields.ForeignKeyField(
        "app.TicketPlateSearchService",
        related_name="plates",
        on_delete=fields.CASCADE,
    )

    plate = fields.CharField(max_length=20)

    class Meta:
        table = "ticket_plate_search_service_plates"
        indexes = (("service_id", "created_at"),)


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
    radar_address = fields.TextField(null=True)
    orientation = fields.TextField(null=True)

    class Meta:
        table = "ticket_radar_search_services"
        indexes = (("ticket_id", "created_at"),)


class TicketRadarSearchServicePlate(Model):
    id = fields.UUIDField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    service = fields.ForeignKeyField(
        "app.TicketRadarSearchService",
        related_name="plates",
        on_delete=fields.CASCADE,
    )

    plate = fields.CharField(max_length=20)

    class Meta:
        table = "ticket_radar_search_service_plates"
        indexes = (("service_id", "created_at"),)


class TicketElectronicFenceService(Model):
    id = fields.UUIDField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    ticket = fields.ForeignKeyField(
        "app.Ticket",
        related_name="electronic_fence_services",
        on_delete=fields.CASCADE,
    )

    plate = fields.CharField(max_length=20, null=True)
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

    period_start = fields.DatetimeField(null=True)
    period_end = fields.DatetimeField(null=True)
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

    plate = fields.CharField(max_length=20, null=True)

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

    period_start = fields.DatetimeField(null=True)
    period_end = fields.DatetimeField(null=True)
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

    plate = fields.CharField(max_length=20, null=True)

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



class Team(Model):
    id = fields.UUIDField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    name = fields.CharField(max_length=120, unique=True) 
    description = fields.TextField(null=True)
    is_active = fields.BooleanField(default=True)

    class Meta:
        table = "teams"



class UserRole(Model):
    id = fields.UUIDField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    user = fields.ForeignKeyField(
        "app.User",
        related_name="roles",
        on_delete=fields.CASCADE,
    )

    role = fields.CharEnumField(
        UserRoleEnum,
        max_length=30,
    )

    class Meta:
        table = "user_roles"
        unique_together = (("user_id", "role"),)
        indexes = (("user_id", "role"),)

class TeamMember(Model):
    id = fields.UUIDField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    team = fields.ForeignKeyField(
        "app.Team",
        related_name="members",
        on_delete=fields.CASCADE,
    )

    user = fields.ForeignKeyField(
        "app.User",
        related_name="team_memberships",
        on_delete=fields.CASCADE,
        unique=True,
    )

    role = fields.CharEnumField(
        UserRoleEnum,
        max_length=30,
    )

    island = fields.ForeignKeyField(
        "app.Island",
        related_name="members",
        null=True,
        on_delete=fields.SET_NULL,
    )

    is_active = fields.BooleanField(default=True)

    class Meta:
        table = "team_members"
        unique_together = (("team_id", "user_id"),)
        indexes = (
            ("team_id", "user_id"),
            ("team_id", "island_id"),
        )

class Island(Model):
    id = fields.UUIDField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    team = fields.ForeignKeyField(
        "app.Team",
        related_name="islands",
        on_delete=fields.CASCADE,
    )

    name = fields.CharField(max_length=40)
    is_active = fields.BooleanField(default=True)

    class Meta:
        table = "islands"
        unique_together = (
            ("team_id", "name"),
        )
        indexes = (
            ("team_id", "is_active"),
            ("team_id", "name"),
        )




class EmailAttachment(Model):

    id = fields.IntField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    email = fields.ForeignKeyField(
        "app.Email",
        related_name="attachments",
        to_field="id",
        on_delete=fields.CASCADE,
    )
    attachment_id = fields.CharField(max_length=1000, null=True)
    filename = fields.CharField(max_length=500)
    mime_type = fields.CharField(max_length=100, default="application/pdf")
    size = fields.IntField(default=0)
    file_path = fields.CharField(max_length=1000)

    class Meta:
        table = "email_attachments"


class StandardizedResponse(Model):
    id = fields.UUIDField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    category = fields.CharField(max_length=100)
    title = fields.CharField(max_length=255)
    when_to_use = fields.TextField(null=True)
    body = fields.TextField()
    is_active = fields.BooleanField(default=True)

    class Meta:
        table = "standardized_responses"
        ordering = ["category", "title"]
        indexes = [
            ("category", "is_active"),
            ("category", "title"),
            ("title",),
            ("is_active",),
        ]