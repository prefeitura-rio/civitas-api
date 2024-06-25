# -*- coding: utf-8 -*-
from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "notificationchannel" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "channel_type" VARCHAR(7) NOT NULL,
    "parameters" JSONB NOT NULL,
    "active" BOOL NOT NULL  DEFAULT True
);
COMMENT ON COLUMN "notificationchannel"."channel_type" IS 'DISCORD: discord';
        CREATE TABLE "monitoredplate_notificationchannel" (
    "monitoredplate_id" UUID NOT NULL REFERENCES "monitoredplate" ("id") ON DELETE CASCADE,
    "notificationchannel_id" UUID NOT NULL REFERENCES "notificationchannel" ("id") ON DELETE CASCADE
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "monitoredplate_notificationchannel";
        DROP TABLE IF EXISTS "notificationchannel";"""
