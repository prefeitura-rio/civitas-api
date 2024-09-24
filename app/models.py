# -*- coding: utf-8 -*-
from typing import Type

from pydantic import BaseModel
from tortoise import fields
from tortoise.exceptions import ValidationError
from tortoise.models import Model
from tortoise.signals import pre_save

from app.enums import ActionTypeEnum, NotificationChannelTypeEnum


class CompanyData(Model):
    id = fields.UUIDField(pk=True)
    cnpj = fields.CharField(max_length=14, unique=True)
    data = fields.JSONField()
    # TODO (future): Expire this data after a certain amount of time?
    created_at = fields.DatetimeField(auto_now_add=True)


@pre_save(CompanyData)
async def validate_company_data(sender, instance: CompanyData, using_db, update_fields):
    """
    This validator checks the following constraints:
    - The CNPJ must have 14 characters and be in a valid format
    - The data must be in the same format as the specified Pydantic model
    """
    from app.pydantic_models import CortexCompanyOut
    from app.utils import validate_cnpj

    if not validate_cnpj(instance.cnpj):
        raise ValidationError("Invalid CNPJ format")

    # Data format validation:
    try:
        CortexCompanyOut(**instance.data)
    except Exception as exc:
        raise ValidationError(str(exc))


class Group(Model):
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=100)
    description = fields.TextField(null=True)


class GroupUser(Model):
    id = fields.UUIDField(pk=True)
    group = fields.ForeignKeyField("app.Group", related_name="group_users")
    user = fields.ForeignKeyField("app.User", related_name="groups")
    is_group_admin = fields.BooleanField(default=False)


class MonitoredPlate(Model):
    id = fields.UUIDField(pk=True)
    operation = fields.ForeignKeyField("app.Operation", related_name="monitored_plates", null=True)
    plate = fields.CharField(max_length=7)
    active = fields.BooleanField(default=True)
    notes = fields.TextField(null=True)
    additional_info = fields.JSONField(null=True)
    notification_channels = fields.ManyToManyField(
        "app.NotificationChannel",
        related_name="monitored_plates",
        through="monitoredplate_notificationchannel",
    )

    async def to_dict(self):
        base_dict = dict(self)
        base_dict["notification_channels"] = [
            channel.id for channel in await self.notification_channels.all()
        ]
        return base_dict


class NotificationChannel(Model):
    id = fields.UUIDField(pk=True)
    title = fields.CharField(max_length=100, null=True)
    channel_type = fields.CharEnumField(enum_type=NotificationChannelTypeEnum)
    parameters = fields.JSONField()
    active = fields.BooleanField(default=True)

    @classmethod
    def get_params_model(cls, channel_type: str) -> Type[BaseModel]:
        class DiscordChannelParams(BaseModel):
            webhook_url: str

        if channel_type == NotificationChannelTypeEnum.DISCORD:
            return DiscordChannelParams
        raise ValidationError(f"Unsupported channel_type: {channel_type}")

    async def validate_parameters(self):
        params_model = self.get_params_model(self.channel_type)
        try:
            params_model(**self.parameters)
        except Exception as exc:
            raise ValidationError(str(exc))


@pre_save(NotificationChannel)
async def validate_notification_channel(
    sender, instance: NotificationChannel, using_db, update_fields
):
    await instance.validate_parameters()


class Operation(Model):
    id = fields.UUIDField(pk=True)
    title = fields.CharField(max_length=100)
    description = fields.TextField(null=True)


class Permission(Model):
    id = fields.UUIDField(pk=True)
    group = fields.ForeignKeyField("app.Group", related_name="permissions")
    action = fields.CharEnumField(enum_type=ActionTypeEnum)
    resource = fields.ForeignKeyField("app.Resource", related_name="permissions")


class PersonData(Model):
    id = fields.UUIDField(pk=True)
    cpf = fields.CharField(max_length=11, unique=True)
    data = fields.JSONField()
    # TODO (future): Expire this data after a certain amount of time?
    created_at = fields.DatetimeField(auto_now_add=True)


@pre_save(PersonData)
async def validate_person_data(sender, instance: PersonData, using_db, update_fields):
    """
    This validator checks the following constraints:
    - The CPF must have 11 characters and be in a valid format
    - The data must be in the same format as the specified Pydantic model
    """
    from app.pydantic_models import CortexPersonOut
    from app.utils import validate_cpf

    if not validate_cpf(instance.cpf):
        raise ValidationError("Invalid CPF format")

    # Data format validation:
    try:
        CortexPersonOut(**instance.data)
    except Exception as exc:
        raise ValidationError(str(exc))


class PlateData(Model):
    id = fields.UUIDField(pk=True)
    plate = fields.CharField(max_length=7, unique=True)
    data = fields.JSONField()
    # TODO (future): Expire this data after a certain amount of time?
    created_at = fields.DatetimeField(auto_now_add=True)


@pre_save(PlateData)
async def validate_plate_data(sender, instance: PlateData, using_db, update_fields):
    """
    This validator checks the following constraints:
    - The plate must have 7 characters and be in a valid format
    - The data must be in the same format as the specified Pydantic model
    """
    from app.pydantic_models import CortexPlacaOut

    # Plate format validation:
    instance.plate = instance.plate.upper()
    # - Must be exactly 7 characters
    if len(instance.plate) != 7:
        raise ValidationError("The plate must have exactly 7 characters")

    # - The 3 first characters must be letters
    if not instance.plate[:3].isalpha():
        raise ValidationError("The first 4 characters of the plate must be letters")

    # - The 4th character must be a number
    if not instance.plate[3].isdigit():
        raise ValidationError("The 5th character of the plate must be a number")

    # - The 5th character must be either a letter or a number
    if not instance.plate[4].isalnum():
        raise ValidationError("The 6th character of the plate must be a letter or a number")

    # - The 6th and 7th characters must be numbers
    if not instance.plate[5:].isdigit():
        raise ValidationError("The last 2 characters of the plate must be numbers")

    # Data format validation:
    try:
        CortexPlacaOut(**instance.data)
    except Exception as exc:
        raise ValidationError(str(exc))


class Resource(Model):
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=255)


class Role(Model):
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    group = fields.ForeignKeyField("app.Group", related_name="roles")
    users = fields.ManyToManyField("app.User", related_name="roles")
    permissions = fields.ManyToManyField("app.Permission", related_name="roles")


@pre_save(Role)
async def validate_role(sender, instance: Role, using_db, update_fields):
    """
    This validator checks the following constraints:
    - The role must have at least one permission
    - All permissions in the role must be from the same group as the role
    - All users in the role must be in the same group as the role
    """
    # The role must have at least one permission
    n_permissions = await instance.permissions.all().count()
    if n_permissions == 0:
        raise ValidationError("The role must have at least one permission")

    # All permissions in the role must be from the same group as the role
    group: Group = await instance.group
    permission: Permission
    for permission in await instance.permissions.all():
        if permission.group != group:
            raise ValidationError(
                "All permissions in the role must be from the same group as the role"
            )

    # All users in the role must be in the same group as the role
    user: User
    for user in await instance.users.all():
        user_ok = False
        user_group: Group
        for user_group in await user.groups.all():
            if user_group == group:
                user_ok = True
                break
        if not user_ok:
            raise ValidationError("All users in the role must be in the same group as the role")


class User(Model):
    id = fields.UUIDField(pk=True)
    username = fields.CharField(max_length=100)
    full_name = fields.CharField(max_length=255, null=True)
    cpf = fields.CharField(max_length=11, null=True)
    registration = fields.CharField(max_length=10, null=True)  # Matrícula
    agency = fields.CharField(max_length=100, null=True)  # Órgão
    sector = fields.CharField(max_length=255, null=True)  # Setor
    email = fields.CharField(max_length=255, null=True)
    is_admin = fields.BooleanField(default=False)
    is_user = fields.BooleanField(default=False)
    is_agent = fields.BooleanField(default=False)


class UserHistory(Model):
    id = fields.UUIDField(pk=True)
    user = fields.ForeignKeyField("app.User", related_name="histories")
    method = fields.CharField(max_length=10)
    path = fields.CharField(max_length=100)
    query_params = fields.JSONField(null=True)
    body = fields.JSONField(null=True)
    status_code = fields.IntField()
    timestamp = fields.DatetimeField(auto_now_add=True)
