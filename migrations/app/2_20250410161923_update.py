from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "reporthistory" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "id_report" VARCHAR(100) NOT NULL,
    "method" VARCHAR(10) NOT NULL,
    "path" VARCHAR(100) NOT NULL,
    "query_params" JSONB,
    "body" JSONB,
    "status_code" INT NOT NULL,
    "timestamp" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "user_id" UUID NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "reporthistory";"""
