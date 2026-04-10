from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
    CREATE TABLE IF NOT EXISTS "standardized_responses" (
        "id" UUID NOT NULL PRIMARY KEY,
        "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        "category" VARCHAR(100) NOT NULL,
        "title" VARCHAR(255) NOT NULL,
        "when_to_use" TEXT,
        "body" TEXT NOT NULL,
        "is_active" BOOL NOT NULL DEFAULT TRUE,
        CONSTRAINT "uid_standardized_responses_category_title"
            UNIQUE ("category", "title")
    );

    CREATE INDEX IF NOT EXISTS "idx_standardized_responses_category_active"
        ON "standardized_responses" ("category", "is_active");

    CREATE INDEX IF NOT EXISTS "idx_standardized_responses_category_title"
        ON "standardized_responses" ("category", "title");

    CREATE INDEX IF NOT EXISTS "idx_standardized_responses_title"
        ON "standardized_responses" ("title");

    CREATE INDEX IF NOT EXISTS "idx_standardized_responses_is_active"
        ON "standardized_responses" ("is_active");

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
    DROP TABLE IF EXISTS "standardized_responses";
    DROP TABLE IF EXISTS "email_templates";
    """
