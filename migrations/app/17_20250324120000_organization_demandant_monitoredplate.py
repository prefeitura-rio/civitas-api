from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
CREATE TABLE IF NOT EXISTS "organization" (
    "id" UUID NOT NULL PRIMARY KEY,
    "name" VARCHAR(150) NOT NULL,
    "organization_type" VARCHAR(255) NOT NULL,
    "acronym" VARCHAR(255) NOT NULL,
    "jurisdiction_level" VARCHAR(255) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO "organization" (
    "id", "name", "organization_type", "acronym", "jurisdiction_level",
    "created_at", "updated_at"
)
SELECT
    "id",
    "title",
    'legacy',
    SUBSTRING(COALESCE("title", ''), 1, 255),
    'unknown',
    "created_at",
    "updated_at"
FROM "operation"
ON CONFLICT ("id") DO NOTHING;

CREATE TABLE IF NOT EXISTS "demandant" (
    "id" UUID NOT NULL PRIMARY KEY,
    "organization_id" UUID NOT NULL REFERENCES "organization" ("id") ON DELETE CASCADE,
    "name" VARCHAR(255),
    "email" VARCHAR(255),
    "phone_1" VARCHAR(20),
    "phone_2" VARCHAR(20),
    "phone_3" VARCHAR(20),
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "monitoredplate_demandant" (
    "id" UUID NOT NULL PRIMARY KEY,
    "monitoredplate_id" UUID NOT NULL REFERENCES "monitoredplate" ("id") ON DELETE CASCADE,
    "demandant_id" UUID NOT NULL REFERENCES "demandant" ("id") ON DELETE CASCADE,
    "reference_number" VARCHAR(50) NOT NULL,
    "valid_until" TIMESTAMPTZ,
    "active" BOOL NOT NULL DEFAULT True,
    "notes" TEXT,
    "additional_info" JSONB,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS "uidx_monitoredplate_demandant_pair"
ON "monitoredplate_demandant" ("monitoredplate_id", "demandant_id");

CREATE TABLE IF NOT EXISTS "monitoredplate_demandant_radar" (
    "id" UUID NOT NULL PRIMARY KEY,
    "monitoredplate_demandant_id" UUID NOT NULL REFERENCES "monitoredplate_demandant" ("id") ON DELETE CASCADE,
    "lpr_equipment_id" UUID NOT NULL,
    "active" BOOL NOT NULL DEFAULT True,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS "uidx_mp_demandant_radar_pair"
ON "monitoredplate_demandant_radar" ("monitoredplate_demandant_id", "lpr_equipment_id");

ALTER TABLE "monitoredplate" ADD COLUMN IF NOT EXISTS "numero_controle" VARCHAR(255);
UPDATE "monitoredplate" SET "numero_controle" = "id"::text WHERE "numero_controle" IS NULL;
ALTER TABLE "monitoredplate" ALTER COLUMN "numero_controle" SET NOT NULL;

ALTER TABLE "monitoredplate" DROP CONSTRAINT IF EXISTS "fk_monitore_operatio_f22f7ca2";
ALTER TABLE "monitoredplate" DROP COLUMN IF EXISTS "operation_id";
ALTER TABLE "monitoredplate" DROP COLUMN IF EXISTS "active";
ALTER TABLE "monitoredplate" DROP COLUMN IF EXISTS "contact_info";
ALTER TABLE "monitoredplate" DROP COLUMN IF EXISTS "additional_info";

CREATE UNIQUE INDEX IF NOT EXISTS "uidx_monitoredplate_plate" ON "monitoredplate" ("plate");
CREATE UNIQUE INDEX IF NOT EXISTS "uidx_monitoredplate_numero_controle" ON "monitoredplate" ("numero_controle");

DROP TABLE IF EXISTS "operation";
"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
CREATE TABLE IF NOT EXISTS "operation" (
    "id" UUID NOT NULL PRIMARY KEY,
    "title" VARCHAR(100) NOT NULL,
    "description" TEXT,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO "operation" ("id", "title", "description", "created_at", "updated_at")
SELECT "id", "name", NULL, "created_at", "updated_at"
FROM "organization"
ON CONFLICT ("id") DO NOTHING;

DROP INDEX IF EXISTS "uidx_monitoredplate_plate";
DROP INDEX IF EXISTS "uidx_monitoredplate_numero_controle";

ALTER TABLE "monitoredplate" ADD COLUMN IF NOT EXISTS "operation_id" UUID REFERENCES "operation" ("id") ON DELETE CASCADE;
ALTER TABLE "monitoredplate" ADD COLUMN IF NOT EXISTS "active" BOOL NOT NULL DEFAULT True;
ALTER TABLE "monitoredplate" ADD COLUMN IF NOT EXISTS "contact_info" TEXT;
ALTER TABLE "monitoredplate" ADD COLUMN IF NOT EXISTS "additional_info" JSONB;

ALTER TABLE "monitoredplate" DROP COLUMN IF EXISTS "numero_controle";

DROP TABLE IF EXISTS "monitoredplate_demandant_radar";
DROP TABLE IF EXISTS "monitoredplate_demandant";
DROP TABLE IF EXISTS "demandant";
DROP TABLE IF EXISTS "organization";
"""
