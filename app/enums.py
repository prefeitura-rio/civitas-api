# -*- coding: utf-8 -*-
from enum import Enum


class ActionTypeEnum(str, Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"


class NotificationChannelTypeEnum(str, Enum):
    DISCORD = "discord"
