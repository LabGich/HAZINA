-- =========================================================
-- HAZINA AUTHENTICATION AND ACCESS CONTROL
-- Migration 26: Create authentication schema
-- =========================================================

CREATE SCHEMA IF NOT EXISTS auth;

-- 1. ORGANIZATIONS
CREATE TABLE IF NOT EXISTS auth.organizations (
    organization_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_organization_name
        CHECK (LENGTH(TRIM(name)) > 0),

    CONSTRAINT chk_organization_slug
        CHECK (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$')
);

-- 2. USERS
CREATE TABLE IF NOT EXISTS auth.users (
    user_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_user_email
        CHECK (email = LOWER(TRIM(email))),

    CONSTRAINT chk_user_full_name
        CHECK (LENGTH(TRIM(full_name)) > 0)
);

-- 3. ROLES
CREATE TABLE IF NOT EXISTS auth.roles (
    role_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    role_code VARCHAR(30) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_role_code
        CHECK (role_code IN ('ADMIN', 'OPERATOR', 'VIEWER'))
);

-- Seed the standard organization roles.
INSERT INTO auth.roles (role_code, description)
VALUES
    ('ADMIN', 'Full organization and user management access.'),
    ('OPERATOR', 'Can upload statements, submit pipeline runs, and view results.'),
    ('VIEWER', 'Read-only access to permitted organization data.')
ON CONFLICT (role_code) DO NOTHING;

-- 4. ORGANIZATION MEMBERSHIPS
CREATE TABLE IF NOT EXISTS auth.organization_memberships (
    membership_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    organization_id BIGINT NOT NULL
        REFERENCES auth.organizations(organization_id)
        ON DELETE RESTRICT,
    user_id BIGINT NOT NULL
        REFERENCES auth.users(user_id)
        ON DELETE RESTRICT,
    role_id BIGINT NOT NULL
        REFERENCES auth.roles(role_id)
        ON DELETE RESTRICT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_organization_user
        UNIQUE (organization_id, user_id)
);

-- Membership lookup indexes.
CREATE INDEX IF NOT EXISTS idx_memberships_user
    ON auth.organization_memberships(user_id);

CREATE INDEX IF NOT EXISTS idx_memberships_organization
    ON auth.organization_memberships(organization_id);

CREATE INDEX IF NOT EXISTS idx_memberships_role
    ON auth.organization_memberships(role_id);

-- User lookup index.
CREATE INDEX IF NOT EXISTS idx_users_active
    ON auth.users(is_active);