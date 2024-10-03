# -*- coding: utf-8 -*-
from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "companydata" ADD "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP;
        ALTER TABLE "monitoredplate" ADD "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP;
        ALTER TABLE "monitoredplate" ADD "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP;
        ALTER TABLE "notificationchannel" ADD "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP;
        ALTER TABLE "notificationchannel" ADD "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP;
        ALTER TABLE "operation" ADD "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP;
        ALTER TABLE "operation" ADD "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP;
        ALTER TABLE "persondata" ADD "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP;
        ALTER TABLE "platedata" ADD "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "operation" DROP COLUMN "updated_at";
        ALTER TABLE "operation" DROP COLUMN "created_at";
        ALTER TABLE "platedata" DROP COLUMN "updated_at";
        ALTER TABLE "persondata" DROP COLUMN "updated_at";
        ALTER TABLE "companydata" DROP COLUMN "updated_at";
        ALTER TABLE "monitoredplate" DROP COLUMN "created_at";
        ALTER TABLE "monitoredplate" DROP COLUMN "updated_at";
        ALTER TABLE "notificationchannel" DROP COLUMN "created_at";
        ALTER TABLE "notificationchannel" DROP COLUMN "updated_at";"""
