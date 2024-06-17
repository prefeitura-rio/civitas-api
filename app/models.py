# -*- coding: utf-8 -*-
from tortoise import fields
from tortoise.models import Model


class MonitoredPlate(Model):
    id = fields.UUIDField(pk=True)
    plate = fields.CharField(max_length=7)


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
