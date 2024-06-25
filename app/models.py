# -*- coding: utf-8 -*-
from typing import Type

from pydantic import BaseModel
from tortoise import fields
from tortoise.exceptions import ValidationError
from tortoise.models import Model
from tortoise.signals import pre_save

from app.enums import NotificationChannelTypeEnum
from app.pydantic_models import DiscordChannelParams


class MonitoredPlate(Model):
    id = fields.UUIDField(pk=True)
    plate = fields.CharField(max_length=7)
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


class UserHistory(Model):
    id = fields.UUIDField(pk=True)
    user = fields.ForeignKeyField("app.User", related_name="histories")
    method = fields.CharField(max_length=10)
    path = fields.CharField(max_length=100)
    query_params = fields.JSONField(null=True)
    body = fields.JSONField(null=True)
    status_code = fields.IntField()
    timestamp = fields.DatetimeField(auto_now_add=True)
