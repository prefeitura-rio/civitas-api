# -*- coding: utf-8 -*-
from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "user" ADD "registration" VARCHAR(10);
        ALTER TABLE "user" ADD "sector" VARCHAR(255);
        ALTER TABLE "user" ADD "email" VARCHAR(255);
        ALTER TABLE "user" ADD "agency" VARCHAR(100);
        ALTER TABLE "user" ADD "cpf" VARCHAR(11);
        ALTER TABLE "user" ADD "full_name" VARCHAR(255);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "user" DROP COLUMN "registration";
        ALTER TABLE "user" DROP COLUMN "sector";
        ALTER TABLE "user" DROP COLUMN "email";
        ALTER TABLE "user" DROP COLUMN "agency";
        ALTER TABLE "user" DROP COLUMN "cpf";
        ALTER TABLE "user" DROP COLUMN "full_name";"""
