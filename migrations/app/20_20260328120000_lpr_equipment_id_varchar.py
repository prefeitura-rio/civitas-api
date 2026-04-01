from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
ALTER TABLE "monitoredplate_demandant_radar"
ALTER COLUMN "lpr_equipment_id" TYPE VARCHAR(64) USING "lpr_equipment_id"::text;
"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
ALTER TABLE "monitoredplate_demandant_radar"
ALTER COLUMN "lpr_equipment_id" TYPE UUID USING "lpr_equipment_id"::uuid;
"""
