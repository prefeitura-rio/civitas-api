from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """

CREATE TABLE IF NOT EXISTS "ticket_types" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(80) NOT NULL UNIQUE,
    "description" TEXT,
    "is_active" BOOL NOT NULL  DEFAULT True
);

     CREATE TABLE IF NOT EXISTS "ticket_natures" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(40) NOT NULL UNIQUE,
    "description" TEXT,
    "is_active" BOOL NOT NULL  DEFAULT True
);

INSERT INTO ticket_types (id, name, description, is_active)
VALUES
(gen_random_uuid(), 'Convencional', NULL, TRUE),
(gen_random_uuid(), 'Levantamento Prévio', NULL, TRUE),
(gen_random_uuid(), 'Requisição Restrita', NULL, TRUE)
ON CONFLICT (name) DO NOTHING;

INSERT INTO ticket_natures (id, name, description, is_active)
VALUES
(gen_random_uuid(), 'Homicídio', NULL, TRUE),
(gen_random_uuid(), 'Latrocínio', NULL, TRUE),
(gen_random_uuid(), 'Tentativa de homicídio', NULL, TRUE),
(gen_random_uuid(), 'Lesão corporal', NULL, TRUE),
(gen_random_uuid(), 'Roubo a Transeunte', NULL, TRUE),
(gen_random_uuid(), 'Roubo de Veículo', NULL, TRUE),
(gen_random_uuid(), 'Roubo de Carga', NULL, TRUE),
(gen_random_uuid(), 'Furto a Transeunte', NULL, TRUE),
(gen_random_uuid(), 'Furto de Veículo', NULL, TRUE),
(gen_random_uuid(), 'Furto de Carga', NULL, TRUE),
(gen_random_uuid(), 'Sequestro', NULL, TRUE),
(gen_random_uuid(), 'Pessoas desaparecidas', NULL, TRUE),
(gen_random_uuid(), 'Extorsão', NULL, TRUE),
(gen_random_uuid(), 'Estelionato', NULL, TRUE),
(gen_random_uuid(), 'Tráfico de drogas', NULL, TRUE),
(gen_random_uuid(), 'Outros delitos', NULL, TRUE),
(gen_random_uuid(), 'Não informado', NULL, TRUE)
ON CONFLICT (name) DO NOTHING;

        CREATE TABLE IF NOT EXISTS "islands" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(40) NOT NULL UNIQUE,
    "description" TEXT,
    "is_active" BOOL NOT NULL  DEFAULT True
);
        CREATE TABLE IF NOT EXISTS "teams" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(120) NOT NULL UNIQUE,
    "description" TEXT,
    "is_active" BOOL NOT NULL  DEFAULT True
);
        CREATE TABLE IF NOT EXISTS "team_members" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "role" VARCHAR(30) NOT NULL,
    "is_active" BOOL NOT NULL  DEFAULT True,
    "island_id" UUID REFERENCES "islands" ("id") ON DELETE SET NULL,
    "team_id" UUID NOT NULL REFERENCES "teams" ("id") ON DELETE CASCADE,
    "user_id" UUID NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_team_member_team_id_a71b13" UNIQUE ("team_id", "user_id")
);
CREATE INDEX IF NOT EXISTS "idx_team_member_team_id_a71b13" ON "team_members" ("team_id", "user_id");
CREATE INDEX IF NOT EXISTS "idx_team_member_team_id_a60c0c" ON "team_members" ("team_id", "island_id");
COMMENT ON COLUMN "team_members"."role" IS 'COORDENADOR: Coordenador\nADMINISTRATIVO: Administrativo\nADJUNTO: Adjunto\nLIDER_DE_ILHA: Líder de Ilha\nOPERADOR: Operador';
        CREATE TABLE IF NOT EXISTS "tickets" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "internal_number" INT GENERATED ALWAYS AS IDENTITY UNIQUE,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "status" VARCHAR(30) NOT NULL  DEFAULT 'PENDENTE',
    "priority" VARCHAR(30) NOT NULL,
    "procedure_number" VARCHAR(60),
    "official_letter_number" VARCHAR(60),
    "base_date" DATE,
    "has_press_nickname" BOOL NOT NULL  DEFAULT False,
    "press_nickname" VARCHAR(120),
    "press_link" VARCHAR(500),
    "requester_name" VARCHAR(120) NOT NULL,
    "requester_phone" VARCHAR(30),
    "requester_email" VARCHAR(254) NOT NULL,
    "nature_id" UUID REFERENCES "ticket_natures" ("id") ON DELETE SET NULL,
    "operation_id" UUID NOT NULL REFERENCES "operation" ("id") ON DELETE RESTRICT,
    "parent_ticket_id" UUID REFERENCES "tickets" ("id") ON DELETE SET NULL,
    "responsible_id" UUID REFERENCES "user" ("id") ON DELETE SET NULL,
    "team_id" UUID REFERENCES "teams" ("id") ON DELETE SET NULL,
    "ticket_type_id" UUID NOT NULL REFERENCES "ticket_types" ("id") ON DELETE RESTRICT
);
COMMENT ON COLUMN "tickets"."status" IS 'PENDENTE: PENDENTE\nRESTRITO: RESTRITO\nBLOQUEADO: BLOQUEADO\nAGUARDANDO_REVISAO: AGUARDANDO_REVISAO\nCONCLUIDO: CONCLUIDO';
COMMENT ON COLUMN "tickets"."priority" IS 'URGENTE: URGENTE\nALTA: ALTA\nROTINA: ROTINA';
        CREATE TABLE IF NOT EXISTS "ticket_attachments" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "filename" VARCHAR(255) NOT NULL,
    "content_type" VARCHAR(120),
    "size_bytes" INT NOT NULL,
    "storage_key" VARCHAR(500) NOT NULL,
    "ticket_id" UUID NOT NULL REFERENCES "tickets" ("id") ON DELETE CASCADE
);
        CREATE TABLE IF NOT EXISTS "ticket_comments" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "body" TEXT NOT NULL,
    "author_id" UUID REFERENCES "user" ("id") ON DELETE SET NULL,
    "ticket_id" UUID NOT NULL REFERENCES "tickets" ("id") ON DELETE CASCADE
);
        CREATE TABLE IF NOT EXISTS "ticket_correlated_plate_services" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "interest_interval_minutes" INT,
    "detection_count" INT,
    "detection" VARCHAR(10),
    "ticket_id" UUID NOT NULL REFERENCES "tickets" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_ticket_corr_ticket__1c88b8" ON "ticket_correlated_plate_services" ("ticket_id", "created_at");
        CREATE TABLE IF NOT EXISTS "ticket_correlated_plate_service_items" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "period_start" TIMESTAMPTZ,
    "period_end" TIMESTAMPTZ,
    "plate" VARCHAR(20),
    "service_id" UUID NOT NULL REFERENCES "ticket_correlated_plate_services" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_ticket_corr_service_cf719d" ON "ticket_correlated_plate_service_items" ("service_id", "created_at");
        CREATE TABLE IF NOT EXISTS "ticket_electronic_fence_services" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "plate" VARCHAR(20),
    "vehicle_observations" TEXT,
    "ticket_id" UUID NOT NULL REFERENCES "tickets" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_ticket_elec_ticket__085623" ON "ticket_electronic_fence_services" ("ticket_id", "created_at");
        CREATE TABLE IF NOT EXISTS "ticket_focal_points" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "name" VARCHAR(120) NOT NULL,
    "phone" VARCHAR(30),
    "email" VARCHAR(254),
    "ticket_id" UUID NOT NULL REFERENCES "tickets" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_ticket_foca_ticket__020dc9" ON "ticket_focal_points" ("ticket_id", "created_at");
        CREATE TABLE IF NOT EXISTS "ticket_histories" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "action" VARCHAR(100) NOT NULL,
    "ticket_id" UUID NOT NULL REFERENCES "tickets" ("id") ON DELETE CASCADE,
    "user_id" UUID NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_ticket_hist_ticket__e03b0e" ON "ticket_histories" ("ticket_id", "created_at");
CREATE INDEX IF NOT EXISTS "idx_ticket_hist_user_id_b4c4bf" ON "ticket_histories" ("user_id", "created_at");
        CREATE TABLE IF NOT EXISTS "ticket_image_analysis_services" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "period_start" TIMESTAMPTZ,
    "period_end" TIMESTAMPTZ,
    "orientation" TEXT,
    "ticket_id" UUID NOT NULL REFERENCES "tickets" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_ticket_imag_ticket__95a1a7" ON "ticket_image_analysis_services" ("ticket_id", "created_at");
        CREATE TABLE IF NOT EXISTS "ticket_image_reservation_services" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "period_start" TIMESTAMPTZ,
    "period_end" TIMESTAMPTZ,
    "orientation" TEXT,
    "ticket_id" UUID NOT NULL REFERENCES "tickets" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_ticket_imag_ticket__322ecb" ON "ticket_image_reservation_services" ("ticket_id", "created_at");
        CREATE TABLE IF NOT EXISTS "ticket_image_search_services" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "period_start" TIMESTAMPTZ,
    "period_end" TIMESTAMPTZ,
    "plate" VARCHAR(20),
    "address" TEXT,
    "description" TEXT,
    "ticket_id" UUID NOT NULL REFERENCES "tickets" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_ticket_imag_ticket__508a81" ON "ticket_image_search_services" ("ticket_id", "created_at");
        CREATE TABLE IF NOT EXISTS "ticket_joint_plate_services" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "interest_interval_minutes" INT,
    "detection_count" INT,
    "detection" VARCHAR(10),
    "ticket_id" UUID NOT NULL REFERENCES "tickets" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_ticket_join_ticket__437f59" ON "ticket_joint_plate_services" ("ticket_id", "created_at");
        CREATE TABLE IF NOT EXISTS "ticket_joint_plate_service_items" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "period_start" TIMESTAMPTZ,
    "period_end" TIMESTAMPTZ,
    "plate" VARCHAR(20),
    "service_id" UUID NOT NULL REFERENCES "ticket_joint_plate_services" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_ticket_join_service_b7535c" ON "ticket_joint_plate_service_items" ("service_id", "created_at");

        CREATE TABLE IF NOT EXISTS "ticket_other_services" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "orientation" TEXT,
    "ticket_id" UUID NOT NULL REFERENCES "tickets" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_ticket_othe_ticket__46e503" ON "ticket_other_services" ("ticket_id", "created_at");
        CREATE TABLE IF NOT EXISTS "ticket_plate_search_services" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "period_start" TIMESTAMPTZ,
    "period_end" TIMESTAMPTZ,
    "plate" VARCHAR(20),
    "ticket_id" UUID NOT NULL REFERENCES "tickets" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_ticket_plat_ticket__84af70" ON "ticket_plate_search_services" ("ticket_id", "created_at");
        CREATE TABLE IF NOT EXISTS "ticket_radar_search_services" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "period_start" TIMESTAMPTZ,
    "period_end" TIMESTAMPTZ,
    "plate" VARCHAR(20),
    "radar_address" TEXT,
    "ticket_id" UUID NOT NULL REFERENCES "tickets" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_ticket_rada_ticket__276771" ON "ticket_radar_search_services" ("ticket_id", "created_at");

        CREATE TABLE IF NOT EXISTS "user_roles" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "role" VARCHAR(30) NOT NULL,
    "user_id" UUID NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_user_roles_user_id_e2d786" UNIQUE ("user_id", "role")
);
CREATE INDEX IF NOT EXISTS "idx_user_roles_user_id_e2d786" ON "user_roles" ("user_id", "role");
COMMENT ON COLUMN "user_roles"."role" IS 'COORDENADOR: Coordenador\nADMINISTRATIVO: Administrativo\nADJUNTO: Adjunto\nLIDER_DE_ILHA: Líder de Ilha\nOPERADOR: Operador';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "islands";
        DROP TABLE IF EXISTS "teams";
        DROP TABLE IF EXISTS "team_members";
        DROP TABLE IF EXISTS "tickets";
        DROP TABLE IF EXISTS "ticket_attachments";
        DROP TABLE IF EXISTS "ticket_comments";
        DROP TABLE IF EXISTS "ticket_correlated_plate_services";
        DROP TABLE IF EXISTS "ticket_correlated_plate_service_items";
        DROP TABLE IF EXISTS "ticket_electronic_fence_services";
        DROP TABLE IF EXISTS "ticket_focal_points";
        DROP TABLE IF EXISTS "ticket_histories";
        DROP TABLE IF EXISTS "ticket_image_analysis_services";
        DROP TABLE IF EXISTS "ticket_image_reservation_services";
        DROP TABLE IF EXISTS "ticket_image_search_services";
        DROP TABLE IF EXISTS "ticket_joint_plate_services";
        DROP TABLE IF EXISTS "ticket_joint_plate_service_items";
        DROP TABLE IF EXISTS "ticket_natures";
        DROP TABLE IF EXISTS "ticket_other_services";
        DROP TABLE IF EXISTS "ticket_plate_search_services";
        DROP TABLE IF EXISTS "ticket_radar_search_services";
        DROP TABLE IF EXISTS "ticket_types";
        DROP TABLE IF EXISTS "user_roles";"""
