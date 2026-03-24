from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
    ALTER TABLE "tickets"
        ADD COLUMN IF NOT EXISTS "responsible_id" UUID;

    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1
            FROM pg_constraint
            WHERE conname = 'fk_tickets_responsible_id_user'
        ) THEN
            ALTER TABLE "tickets"
                ADD CONSTRAINT "fk_tickets_responsible_id_user"
                FOREIGN KEY ("responsible_id")
                REFERENCES "user" ("id")
                ON DELETE SET NULL;
        END IF;
    END $$;

    ALTER TABLE "tickets"
        DROP COLUMN IF EXISTS "team_id";

    ALTER TABLE "tickets"
        ADD COLUMN "team_id" UUID;

    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1
            FROM pg_constraint
            WHERE conname = 'fk_tickets_team_id_teams'
        ) THEN
            ALTER TABLE "tickets"
                ADD CONSTRAINT "fk_tickets_team_id_teams"
                FOREIGN KEY ("team_id")
                REFERENCES "teams" ("id")
                ON DELETE SET NULL;
        END IF;
    END $$;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
    ALTER TABLE "tickets" DROP CONSTRAINT IF EXISTS "fk_tickets_responsible_id_user";
    ALTER TABLE "tickets" DROP CONSTRAINT IF EXISTS "fk_tickets_team_id_teams";

    ALTER TABLE "tickets" DROP COLUMN IF EXISTS "responsible_id";
    ALTER TABLE "tickets" DROP COLUMN IF EXISTS "team_id";

    ALTER TABLE "tickets"
        ADD COLUMN "team_id" VARCHAR(80);
    """