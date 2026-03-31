from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "ticket_plate_search_service_plates" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "plate" VARCHAR(20) NOT NULL,
    "service_id" UUID NOT NULL REFERENCES "ticket_plate_search_services" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_ticket_plat_plate_serv_cf8a21" ON "ticket_plate_search_service_plates" ("service_id", "created_at");

INSERT INTO "ticket_plate_search_service_plates" ("id", "created_at", "plate", "service_id")
SELECT gen_random_uuid(), s."created_at", trim(s."plate"), s."id"
FROM "ticket_plate_search_services" s
WHERE s."plate" IS NOT NULL AND trim(s."plate") <> '';

ALTER TABLE "ticket_plate_search_services" DROP COLUMN IF EXISTS "plate";

        CREATE TABLE IF NOT EXISTS "ticket_radar_search_service_plates" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "plate" VARCHAR(20) NOT NULL,
    "service_id" UUID NOT NULL REFERENCES "ticket_radar_search_services" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_ticket_rada_plate_serv_9e4b12" ON "ticket_radar_search_service_plates" ("service_id", "created_at");

INSERT INTO "ticket_radar_search_service_plates" ("id", "created_at", "plate", "service_id")
SELECT gen_random_uuid(), s."created_at", trim(s."plate"), s."id"
FROM "ticket_radar_search_services" s
WHERE s."plate" IS NOT NULL AND trim(s."plate") <> '';

ALTER TABLE "ticket_radar_search_services" DROP COLUMN IF EXISTS "plate";

        ALTER TABLE "ticket_correlated_plate_services" ADD COLUMN IF NOT EXISTS "period_start" TIMESTAMPTZ;
        ALTER TABLE "ticket_correlated_plate_services" ADD COLUMN IF NOT EXISTS "period_end" TIMESTAMPTZ;

        UPDATE "ticket_correlated_plate_services" s
        SET
            "period_start" = i."period_start",
            "period_end" = i."period_end"
        FROM (
            SELECT DISTINCT ON ("service_id") "service_id", "period_start", "period_end"
            FROM "ticket_correlated_plate_service_items"
            ORDER BY "service_id", "created_at"
        ) i
        WHERE s."id" = i."service_id";

        ALTER TABLE "ticket_correlated_plate_service_items" DROP COLUMN IF EXISTS "period_start";
        ALTER TABLE "ticket_correlated_plate_service_items" DROP COLUMN IF EXISTS "period_end";

        ALTER TABLE "ticket_joint_plate_services" ADD COLUMN IF NOT EXISTS "period_start" TIMESTAMPTZ;
        ALTER TABLE "ticket_joint_plate_services" ADD COLUMN IF NOT EXISTS "period_end" TIMESTAMPTZ;

        UPDATE "ticket_joint_plate_services" s
        SET
            "period_start" = i."period_start",
            "period_end" = i."period_end"
        FROM (
            SELECT DISTINCT ON ("service_id") "service_id", "period_start", "period_end"
            FROM "ticket_joint_plate_service_items"
            ORDER BY "service_id", "created_at"
        ) i
        WHERE s."id" = i."service_id";

        ALTER TABLE "ticket_joint_plate_service_items" DROP COLUMN IF EXISTS "period_start";
        ALTER TABLE "ticket_joint_plate_service_items" DROP COLUMN IF EXISTS "period_end";

        ALTER TABLE "ticket_radar_search_services" ADD COLUMN IF NOT EXISTS "orientation" TEXT;

        ALTER TABLE "tickets" ADD COLUMN IF NOT EXISTS "procedure_operation_id" UUID REFERENCES "operation" ("id") ON DELETE RESTRICT;
"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "tickets" DROP COLUMN IF EXISTS "procedure_operation_id";

        ALTER TABLE "ticket_radar_search_services" DROP COLUMN IF EXISTS "orientation";

        ALTER TABLE "ticket_joint_plate_service_items" ADD COLUMN IF NOT EXISTS "period_start" TIMESTAMPTZ;
        ALTER TABLE "ticket_joint_plate_service_items" ADD COLUMN IF NOT EXISTS "period_end" TIMESTAMPTZ;

        UPDATE "ticket_joint_plate_service_items" it
        SET
            "period_start" = s."period_start",
            "period_end" = s."period_end"
        FROM "ticket_joint_plate_services" s
        WHERE it."service_id" = s."id";

        ALTER TABLE "ticket_joint_plate_services" DROP COLUMN IF EXISTS "period_start";
        ALTER TABLE "ticket_joint_plate_services" DROP COLUMN IF EXISTS "period_end";

        ALTER TABLE "ticket_correlated_plate_service_items" ADD COLUMN IF NOT EXISTS "period_start" TIMESTAMPTZ;
        ALTER TABLE "ticket_correlated_plate_service_items" ADD COLUMN IF NOT EXISTS "period_end" TIMESTAMPTZ;

        UPDATE "ticket_correlated_plate_service_items" it
        SET
            "period_start" = s."period_start",
            "period_end" = s."period_end"
        FROM "ticket_correlated_plate_services" s
        WHERE it."service_id" = s."id";

        ALTER TABLE "ticket_correlated_plate_services" DROP COLUMN IF EXISTS "period_start";
        ALTER TABLE "ticket_correlated_plate_services" DROP COLUMN IF EXISTS "period_end";

        ALTER TABLE "ticket_radar_search_services" ADD COLUMN IF NOT EXISTS "plate" VARCHAR(20);

        UPDATE "ticket_radar_search_services" s
        SET "plate" = sub."plate"
        FROM (
            SELECT DISTINCT ON (p."service_id") p."service_id", p."plate"
            FROM "ticket_radar_search_service_plates" p
            ORDER BY p."service_id", p."created_at" ASC
        ) sub
        WHERE s."id" = sub."service_id";

        DROP TABLE IF EXISTS "ticket_radar_search_service_plates";

        ALTER TABLE "ticket_plate_search_services" ADD COLUMN IF NOT EXISTS "plate" VARCHAR(20);

        UPDATE "ticket_plate_search_services" s
        SET "plate" = sub."plate"
        FROM (
            SELECT DISTINCT ON (p."service_id") p."service_id", p."plate"
            FROM "ticket_plate_search_service_plates" p
            ORDER BY p."service_id", p."created_at" ASC
        ) sub
        WHERE s."id" = sub."service_id";

        DROP TABLE IF EXISTS "ticket_plate_search_service_plates";
"""
