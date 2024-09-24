# -*- coding: utf-8 -*-
from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "user" ADD "is_user" BOOL NOT NULL  DEFAULT False;
        ALTER TABLE "user" ADD "is_agent" BOOL NOT NULL  DEFAULT False;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "user" DROP COLUMN "is_user";
        ALTER TABLE "user" DROP COLUMN "is_agent";"""
