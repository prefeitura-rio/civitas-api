from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "tickets"
            ADD COLUMN IF NOT EXISTS "correspondence_street" VARCHAR(255);

        ALTER TABLE "tickets"
            ADD COLUMN IF NOT EXISTS "correspondence_neighborhood" VARCHAR(120);

        ALTER TABLE "tickets"
            ADD COLUMN IF NOT EXISTS "correspondence_number" VARCHAR(20);

        ALTER TABLE "tickets"
            ADD COLUMN IF NOT EXISTS "has_correspondence_address" BOOL NOT NULL DEFAULT False;

        ALTER TABLE "tickets"
            ALTER COLUMN "priority" DROP NOT NULL;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "tickets"
            DROP COLUMN IF EXISTS "correspondence_street";

        ALTER TABLE "tickets"
            DROP COLUMN IF EXISTS "correspondence_neighborhood";

        ALTER TABLE "tickets"
            DROP COLUMN IF EXISTS "correspondence_number";

        ALTER TABLE "tickets"
            DROP COLUMN IF EXISTS "has_correspondence_address";

        ALTER TABLE "tickets"
            ALTER COLUMN "priority" SET NOT NULL;
    """