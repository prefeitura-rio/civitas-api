from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "email_templates" (
            "id" UUID NOT NULL PRIMARY KEY,
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "title" VARCHAR(255) NOT NULL UNIQUE,
            "body_html" TEXT NOT NULL,
            "is_active" BOOL NOT NULL DEFAULT TRUE
        );
        CREATE INDEX IF NOT EXISTS "idx_email_templates_title"
            ON "email_templates" ("title");
        CREATE INDEX IF NOT EXISTS "idx_email_templates_is_active"
            ON "email_templates" ("is_active");
        CREATE INDEX IF NOT EXISTS "idx_email_templates_title_is_active"
            ON "email_templates" ("title", "is_active");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "email_templates";
    """