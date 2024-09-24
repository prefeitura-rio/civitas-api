# -*- coding: utf-8 -*-
from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "role_user";
        DROP TABLE IF EXISTS "role";
        DROP TABLE IF EXISTS "groupuser";
        DROP TABLE IF EXISTS "permission";
        DROP TABLE IF EXISTS "group";
        DROP TABLE IF EXISTS "resource";
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE "role_user" (
    "user_id" UUID NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE,
    "role_id" UUID NOT NULL REFERENCES "role" ("id") ON DELETE CASCADE
);"""
