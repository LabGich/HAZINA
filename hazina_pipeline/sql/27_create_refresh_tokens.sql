-- =========================================================
-- HAZINA AUTHENTICATION
-- Migration 27: Persistent refresh-token sessions
-- =========================================================

CREATE TABLE IF NOT EXISTS auth.refresh_tokens (
    refresh_token_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    user_id BIGINT NOT NULL
        REFERENCES auth.users(user_id)
        ON DELETE RESTRICT,

    organization_id BIGINT NOT NULL
        REFERENCES auth.organizations(organization_id)
        ON DELETE RESTRICT,

    token_jti UUID NOT NULL UNIQUE,

    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,

    replaced_by_jti UUID,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user
    ON auth.refresh_tokens(user_id);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_organization
    ON auth.refresh_tokens(organization_id);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_active
    ON auth.refresh_tokens(token_jti)
    WHERE revoked_at IS NULL;