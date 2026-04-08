from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_team_member_team_id_a60c0c";
        DROP INDEX IF EXISTS "idx_islands_name_b45364";
        ALTER TABLE "islands" DROP CONSTRAINT IF EXISTS "islands_name_key";

        ALTER TABLE "islands"
            ADD COLUMN IF NOT EXISTS "team_id" UUID;

        ALTER TABLE "islands"
            DROP COLUMN IF EXISTS "description";

        CREATE UNIQUE INDEX IF NOT EXISTS "uid_islands_team_id_72203d"
            ON "islands" ("team_id", "name");

        CREATE UNIQUE INDEX IF NOT EXISTS "uid_islands_team_id_bc33ef"
            ON "islands" ("team_id", "id");

        CREATE INDEX IF NOT EXISTS "idx_islands_team_id_72203d"
            ON "islands" ("team_id", "name");

        CREATE INDEX IF NOT EXISTS "idx_islands_team_id_bc33ef"
            ON "islands" ("team_id", "id");

        CREATE INDEX IF NOT EXISTS "idx_islands_team_id_1c1cf8"
            ON "islands" ("team_id", "is_active");

        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'fk_islands_teams_644c0522'
            ) THEN
                ALTER TABLE "islands"
                ADD CONSTRAINT "fk_islands_teams_644c0522"
                FOREIGN KEY ("team_id") REFERENCES "teams" ("id") ON DELETE CASCADE;
            END IF;
        END
        $$;

        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'islands'
                  AND column_name = 'team_id'
                  AND is_nullable = 'YES'
            ) AND NOT EXISTS (
                SELECT 1
                FROM "islands"
                WHERE "team_id" IS NULL
            ) THEN
                ALTER TABLE "islands"
                ALTER COLUMN "team_id" SET NOT NULL;
            END IF;
        END
        $$;

        CREATE INDEX IF NOT EXISTS "idx_team_member_team_id_a60c0c"
            ON "team_members" ("team_id", "island_id");
        ALTER TABLE "islands" DROP CONSTRAINT IF EXISTS "islands_name_key";

    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_team_member_team_id_a60c0c";

        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'fk_islands_teams_644c0522'
            ) THEN
                ALTER TABLE "islands"
                DROP CONSTRAINT "fk_islands_teams_644c0522";
            END IF;
        END
        $$;

        DROP INDEX IF EXISTS "idx_islands_team_id_1c1cf8";
        DROP INDEX IF EXISTS "idx_islands_team_id_bc33ef";
        DROP INDEX IF EXISTS "idx_islands_team_id_72203d";
        DROP INDEX IF EXISTS "uid_islands_team_id_bc33ef";
        DROP INDEX IF EXISTS "uid_islands_team_id_72203d";

        ALTER TABLE "islands"
            ADD COLUMN IF NOT EXISTS "description" TEXT;

        ALTER TABLE "islands"
            DROP COLUMN IF EXISTS "team_id";

        CREATE UNIQUE INDEX IF NOT EXISTS "uid_islands_name_b45364"
            ON "islands" ("name");

        CREATE INDEX IF NOT EXISTS "idx_team_member_team_id_a60c0c"
            ON "team_members" ("team_id", "island_id");

        ALTER TABLE "islands"
            ADD CONSTRAINT "islands_name_key" UNIQUE ("name");
    """