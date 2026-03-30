from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "emails" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "message_id" VARCHAR(255) NOT NULL UNIQUE,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "thread_id" VARCHAR(255),
    "from_address" VARCHAR(500),
    "from_name" VARCHAR(255),
    "to_address" VARCHAR(500),
    "subject" VARCHAR(1000),
    "snippet" TEXT,
    "body_preview" TEXT,
    "date" TIMESTAMPTZ,
    "internal_date" BIGINT,
    "has_attachments" BOOL NOT NULL  DEFAULT False,
    "label_ids" TEXT,
    "status" VARCHAR(30) NOT NULL  DEFAULT 'Não Lidos'
);
CREATE INDEX IF NOT EXISTS "idx_emails_thread__cd1d55" ON "emails" ("thread_id");
COMMENT ON COLUMN "emails"."status" IS 'RESPONDIDO: Respondido\nNAO_LIDO: Não Lido\nAGUARDANDO_RESPOSTA: Aguardando Resposta\nSPAM: Spam';
        CREATE TABLE IF NOT EXISTS "email_attachments" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "attachment_id" VARCHAR(1000),
    "filename" VARCHAR(500) NOT NULL,
    "mime_type" VARCHAR(100) NOT NULL  DEFAULT 'application/pdf',
    "size" INT NOT NULL  DEFAULT 0,
    "file_path" VARCHAR(1000) NOT NULL,
    "email_id" UUID NOT NULL REFERENCES "emails" ("id") ON DELETE CASCADE
);
        CREATE TABLE "ticket_emails" (
    "ticket_id" UUID NOT NULL REFERENCES "tickets" ("id") ON DELETE CASCADE,
    "email_id" UUID NOT NULL REFERENCES "emails" ("id") ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS "email_sync_state" (
    "id" INT NOT NULL  PRIMARY KEY,
    "watermark_internal_date_ms" BIGINT,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
        INSERT INTO "email_sync_state" ("id", "watermark_internal_date_ms")
        VALUES (1, NULL)
        ON CONFLICT ("id") DO NOTHING;

"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "ticket_emails";
        DROP TABLE IF EXISTS "emails";
        DROP TABLE IF EXISTS "email_attachments";
        DROP TABLE IF EXISTS "email_sync_state";"""
