from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
ALTER TABLE "monitoredplate_demandant"
ADD COLUMN IF NOT EXISTS "validity_warning_sent_at" TIMESTAMPTZ NULL;
"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
ALTER TABLE "monitoredplate_demandant"
DROP COLUMN IF EXISTS "validity_warning_sent_at";
"""
