from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "tickets" ADD "correspondence_street" VARCHAR(255);
        ALTER TABLE "tickets" ADD "correspondence_neighborhood" VARCHAR(120);
        ALTER TABLE "tickets" ADD "correspondence_number" VARCHAR(20);
        ALTER TABLE "tickets" ADD "has_correspondence_address" BOOL NOT NULL  DEFAULT False;
        ALTER TABLE "tickets" ALTER COLUMN "priority" DROP NOT NULL;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "tickets" DROP COLUMN "correspondence_street";
        ALTER TABLE "tickets" DROP COLUMN "correspondence_neighborhood";
        ALTER TABLE "tickets" DROP COLUMN "correspondence_number";
        ALTER TABLE "tickets" DROP COLUMN "has_correspondence_address";
        ALTER TABLE "tickets" ALTER COLUMN "priority" SET NOT NULL;"""
