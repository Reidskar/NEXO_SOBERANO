-- ═══════════════════════════════════════════════════════════════
--  NEXO SOBERANO — Inicialización PostgreSQL Multi-Tenant
--  Ejecutado automáticamente por Docker en primer arranque
-- ═══════════════════════════════════════════════════════════════

-- Extensiones útiles
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";      -- UUIDs nativos
CREATE EXTENSION IF NOT EXISTS "pg_trgm";        -- Búsqueda texto fuzzy
CREATE EXTENSION IF NOT EXISTS "btree_gin";      -- Índices GIN en columnas simples

-- ── SCHEMA PÚBLICO: tablas del sistema (superadmin) ───────────

-- Tenants (empresas / clientes)
CREATE TABLE IF NOT EXISTS tenants (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug        VARCHAR(63) UNIQUE NOT NULL,     -- ej: "empresa-abc"
    name        VARCHAR(255) NOT NULL,
    plan        VARCHAR(32) DEFAULT 'starter',   -- starter | pro | enterprise
    -- Límites por plan
    max_users          INT DEFAULT 5,
    max_tokens_dia     INT DEFAULT 50000,        -- Límite tokens/día por tenant
    max_storage_mb     INT DEFAULT 500,
    -- Estado
    active      BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Usuarios del sistema
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email           VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role            VARCHAR(32) DEFAULT 'member',  -- owner | admin | member
    active          BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    last_login      TIMESTAMPTZ,
    UNIQUE(tenant_id, email)
);

-- Sessions / JWT tracking
CREATE TABLE IF NOT EXISTS sessions (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    token_hash  VARCHAR(255) UNIQUE NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── SCHEMA POR TENANT: función helper ────────────────────────
-- Crea un schema aislado para cada tenant nuevo
CREATE OR REPLACE FUNCTION create_tenant_schema(tenant_slug VARCHAR)
RETURNS VOID AS $$
DECLARE
    schema_name VARCHAR := 'tenant_' || replace(tenant_slug, '-', '_');
BEGIN
    EXECUTE format('CREATE SCHEMA IF NOT EXISTS %I', schema_name);

    -- Perfiles cognitivos
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS %I.cognitive_profiles (
            id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id         UUID NOT NULL,
            learning_style  VARCHAR(32) DEFAULT ''reading'',
            vocabulary      VARCHAR(32) DEFAULT ''simple'',
            content_length  VARCHAR(32) DEFAULT ''200w'',
            tone            VARCHAR(32) DEFAULT ''casual'',
            presentation    VARCHAR(32) DEFAULT ''bullet'',
            sequence        VARCHAR(32) DEFAULT ''linear'',
            depth_level     VARCHAR(32) DEFAULT ''surface'',
            example_mode    VARCHAR(32) DEFAULT ''practical'',
            format_pref     VARCHAR(32) DEFAULT ''text'',
            expertise       JSONB DEFAULT ''{}'',
            updated_at      TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(user_id)
        )', schema_name);

    -- Conversaciones
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS %I.conversations (
            id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id     UUID NOT NULL,
            title       VARCHAR(255),
            created_at  TIMESTAMPTZ DEFAULT NOW(),
            updated_at  TIMESTAMPTZ DEFAULT NOW()
        )', schema_name);

    -- Mensajes
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS %I.messages (
            id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            conversation_id UUID NOT NULL,
            user_id         UUID NOT NULL,
            role            VARCHAR(16) NOT NULL,  -- user | assistant | system
            content         TEXT NOT NULL,
            tokens_used     INT DEFAULT 0,
            model_used      VARCHAR(64),
            created_at      TIMESTAMPTZ DEFAULT NOW()
        )', schema_name);

    -- Índice para traer historial rápido
    EXECUTE format('
        CREATE INDEX IF NOT EXISTS idx_%s_messages_conv
        ON %I.messages(conversation_id, created_at DESC)',
        schema_name, schema_name);

    -- Notificaciones / cola de email
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS %I.email_queue (
            id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id     UUID NOT NULL,
            status      VARCHAR(16) DEFAULT ''pending'',
            subject     VARCHAR(255),
            html_content TEXT,
            sent_at     TIMESTAMPTZ,
            created_at  TIMESTAMPTZ DEFAULT NOW()
        )', schema_name);

    -- Tracking de costos por tenant
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS %I.api_costs (
            id          BIGSERIAL PRIMARY KEY,
            user_id     UUID,
            model       VARCHAR(64) NOT NULL,
            tokens_in   INT NOT NULL DEFAULT 0,
            tokens_out  INT NOT NULL DEFAULT 0,
            operation   VARCHAR(64),
            fecha       DATE DEFAULT CURRENT_DATE,
            created_at  TIMESTAMPTZ DEFAULT NOW()
        )', schema_name);

    -- Índice para sumar tokens del día rápido
    EXECUTE format('
        CREATE INDEX IF NOT EXISTS idx_%s_costs_fecha
        ON %I.api_costs(fecha)',
        schema_name, schema_name);

    -- Calendario
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS %I.calendar_events (
            id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id     UUID NOT NULL,
            source      VARCHAR(32),
            external_id VARCHAR(255),
            title       VARCHAR(512),
            start_time  TIMESTAMPTZ,
            end_time    TIMESTAMPTZ,
            synced_at   TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(user_id, source, external_id)
        )', schema_name);

    -- Credenciales OAuth del tenant (cifradas en aplicación)
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS %I.oauth_credentials (
            id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id     UUID NOT NULL,
            provider    VARCHAR(32) NOT NULL,
            access_token_enc  TEXT,
            refresh_token_enc TEXT,
            expires_at  TIMESTAMPTZ,
            updated_at  TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(user_id, provider)
        )', schema_name);

    RAISE NOTICE 'Schema % creado exitosamente', schema_name;
END;
$$ LANGUAGE plpgsql;

-- ── ÍNDICES GLOBALES ──────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_users_tenant    ON users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_users_email     ON users(email);
CREATE INDEX IF NOT EXISTS idx_sessions_token  ON sessions(token_hash);
CREATE INDEX IF NOT EXISTS idx_sessions_expiry ON sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_tenants_slug    ON tenants(slug);

-- ── TENANT DEMO (para desarrollo) ────────────────────────────
INSERT INTO tenants (slug, name, plan, max_tokens_dia)
VALUES ('demo', 'Tenant Demo', 'pro', 200000)
ON CONFLICT (slug) DO NOTHING;

SELECT create_tenant_schema('demo');

RAISE NOTICE '✅ Base de datos NEXO SOBERANO inicializada';
