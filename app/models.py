# -*- coding: utf-8 -*-
from tortoise import fields
from tortoise.models import Model


class User(Model):
    id = fields.UUIDField(pk=True)
    username = fields.CharField(max_length=100)
    is_admin = fields.BooleanField(default=False)
