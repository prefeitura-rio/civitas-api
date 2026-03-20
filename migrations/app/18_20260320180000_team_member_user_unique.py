# -*- coding: utf-8 -*-
from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uid_team_members_user_id_unique'
            ) THEN
                ALTER TABLE "team_members"
                ADD CONSTRAINT "uid_team_members_user_id_unique" UNIQUE ("user_id");
            END IF;
        END $$;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "team_members" DROP CONSTRAINT IF EXISTS "uid_team_members_user_id_unique";
    """
