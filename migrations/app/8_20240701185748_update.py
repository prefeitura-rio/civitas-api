# -*- coding: utf-8 -*-
from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "monitoredplate" ADD "active" BOOL NOT NULL  DEFAULT True;
        ALTER TABLE "monitoredplate" ADD "operation_id" UUID;
        CREATE TABLE IF NOT EXISTS "operation" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "title" VARCHAR(100) NOT NULL,
    "description" TEXT
);
        ALTER TABLE "monitoredplate" ADD CONSTRAINT "fk_monitore_operatio_f22f7ca2" FOREIGN KEY ("operation_id") REFERENCES "operation" ("id") ON DELETE CASCADE;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "monitoredplate" DROP CONSTRAINT "fk_monitore_operatio_f22f7ca2";
        ALTER TABLE "monitoredplate" DROP COLUMN "active";
        ALTER TABLE "monitoredplate" DROP COLUMN "operation_id";
        DROP TABLE IF EXISTS "operation";"""
