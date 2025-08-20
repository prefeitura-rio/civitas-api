# -*- coding: utf-8 -*-
from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        -- Synchronization migration with production
        -- Ensures development is equal to production
        
        DO $$
        BEGIN
            -- Check and add User columns (if not exists)
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='user' AND column_name='full_name') THEN
                ALTER TABLE "user" ADD COLUMN "full_name" VARCHAR(255);
                RAISE NOTICE 'Added full_name column';
            END IF;
            
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='user' AND column_name='cpf') THEN
                ALTER TABLE "user" ADD COLUMN "cpf" VARCHAR(11);
                RAISE NOTICE 'Added cpf column';
            END IF;
            
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='user' AND column_name='registration') THEN
                ALTER TABLE "user" ADD COLUMN "registration" VARCHAR(10);
                RAISE NOTICE 'Added registration column';
            END IF;
            
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='user' AND column_name='agency') THEN
                ALTER TABLE "user" ADD COLUMN "agency" VARCHAR(100);
                RAISE NOTICE 'Added agency column';
            END IF;
            
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='user' AND column_name='sector') THEN
                ALTER TABLE "user" ADD COLUMN "sector" VARCHAR(255);
                RAISE NOTICE 'Added sector column';
            END IF;
            
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='user' AND column_name='email') THEN
                ALTER TABLE "user" ADD COLUMN "email" VARCHAR(255);
                RAISE NOTICE 'Added email column';
            END IF;
            
            -- Check and create reporthistory if not exists
            IF NOT EXISTS (SELECT 1 FROM information_schema.tables 
                          WHERE table_name='reporthistory') THEN
                CREATE TABLE "reporthistory" (
                    "id" UUID NOT NULL PRIMARY KEY,
                    "id_report" VARCHAR(100) NOT NULL,
                    "method" VARCHAR(10) NOT NULL,
                    "path" VARCHAR(100) NOT NULL,
                    "query_params" JSONB,
                    "body" JSONB,
                    "status_code" INT NOT NULL,
                    "timestamp" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    "user_id" UUID NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
                );
                RAISE NOTICE 'Created reporthistory table';
            END IF;
            
        END $$;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        -- Downgrade: Do nothing in production for safety
        -- Can be executed manually if necessary
        RAISE NOTICE 'Downgrade synchronization - execute manually if necessary';
    """