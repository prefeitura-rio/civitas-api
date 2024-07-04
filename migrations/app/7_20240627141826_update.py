# -*- coding: utf-8 -*-
from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "group" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "name" VARCHAR(100) NOT NULL,
    "description" TEXT
);
        CREATE TABLE IF NOT EXISTS "groupuser" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "is_group_admin" BOOL NOT NULL  DEFAULT False,
    "group_id" UUID NOT NULL REFERENCES "group" ("id") ON DELETE CASCADE,
    "user_id" UUID NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
        CREATE TABLE IF NOT EXISTS "resource" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL
);
        CREATE TABLE IF NOT EXISTS "permission" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "action" VARCHAR(6) NOT NULL,
    "group_id" UUID NOT NULL REFERENCES "group" ("id") ON DELETE CASCADE,
    "resource_id" UUID NOT NULL REFERENCES "resource" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "permission"."action" IS 'CREATE: create\nREAD: read\nUPDATE: update\nDELETE: delete';
        CREATE TABLE IF NOT EXISTS "role" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "description" TEXT,
    "group_id" UUID NOT NULL REFERENCES "group" ("id") ON DELETE CASCADE
);
        CREATE TABLE "role_user" (
    "user_id" UUID NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE,
    "role_id" UUID NOT NULL REFERENCES "role" ("id") ON DELETE CASCADE
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "role_user";
        DROP TABLE IF EXISTS "group";
        DROP TABLE IF EXISTS "groupuser";
        DROP TABLE IF EXISTS "permission";
        DROP TABLE IF EXISTS "resource";
        DROP TABLE IF EXISTS "role";"""
