from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
DROP INDEX IF EXISTS "uidx_monitoredplate_numero_controle";
ALTER TABLE "monitoredplate" DROP COLUMN IF EXISTS "numero_controle";
"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
ALTER TABLE "monitoredplate" ADD COLUMN IF NOT EXISTS "numero_controle" VARCHAR(255);
UPDATE "monitoredplate" SET "numero_controle" = "id"::text WHERE "numero_controle" IS NULL;
ALTER TABLE "monitoredplate" ALTER COLUMN "numero_controle" SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS "uidx_monitoredplate_numero_controle"
ON "monitoredplate" ("numero_controle");
"""
