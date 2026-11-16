from hazina_pipeline.database.connection import get_database_connection

from datetime import datetime, timezone
from uuid import UUID


class AuthService:
    """Database operations for Hazina authentication."""

    @staticmethod
    def create_organization(name: str, slug: str) -> dict:
        name = name.strip()
        slug = slug.strip().lower()

        if not name or not slug:
            raise ValueError("Organization name and slug are required.")

        with get_database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO auth.organizations (name, slug)
                    VALUES (%s, %s)
                    RETURNING organization_id, name, slug, is_active,
                              created_at;
                    """,
                    (name, slug),
                )
                row = cursor.fetchone()

        return {
            "organization_id": row[0],
            "name": row[1],
            "slug": row[2],
            "is_active": row[3],
            "created_at": row[4],
        }

    @staticmethod
    def get_organization(organization_id: int) -> dict | None:
        with get_database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT organization_id, name, slug, is_active,
                           created_at
                    FROM auth.organizations
                    WHERE organization_id = %s;
                    """,
                    (organization_id,),
                )
                row = cursor.fetchone()

        if row is None:
            return None

        return {
            "organization_id": row[0],
            "name": row[1],
            "slug": row[2],
            "is_active": row[3],
            "created_at": row[4],
        }

    @staticmethod
    def create_user(email: str, password_hash: str, full_name: str) -> dict:
        email = email.strip().lower()
        full_name = full_name.strip()

        if not email or not password_hash or not full_name:
            raise ValueError(
                "Email, password hash, and full name are required."
            )

        with get_database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO auth.users (
                        email, password_hash, full_name
                    )
                    VALUES (%s, %s, %s)
                    RETURNING user_id, email, full_name, is_active,
                              email_verified, created_at;
                    """,
                    (email, password_hash, full_name),
                )
                row = cursor.fetchone()

        return {
            "user_id": row[0],
            "email": row[1],
            "full_name": row[2],
            "is_active": row[3],
            "email_verified": row[4],
            "created_at": row[5],
        }

    @staticmethod
    def get_user_by_email(email: str) -> dict | None:
        email = email.strip().lower()

        with get_database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT user_id, email, password_hash, full_name,
                           is_active, email_verified, created_at
                    FROM auth.users
                    WHERE email = %s;
                    """,
                    (email,),
                )
                row = cursor.fetchone()

        if row is None:
            return None

        return {
            "user_id": row[0],
            "email": row[1],
            "password_hash": row[2],
            "full_name": row[3],
            "is_active": row[4],
            "email_verified": row[5],
            "created_at": row[6],
        }

    
    @staticmethod
    def create_membership(
        organization_id: int,
        user_id: int,
        role_code: str,
    ) -> dict:
        if (
            isinstance(organization_id, bool)
            or not isinstance(organization_id, int)
            or organization_id <= 0
        ):
            raise ValueError("A valid organization_id is required.")

        if (
            isinstance(user_id, bool)
            or not isinstance(user_id, int)
            or user_id <= 0
        ):
            raise ValueError("A valid user_id is required.")

        role_code = role_code.strip().upper()

        if not role_code:
            raise ValueError("A role code is required.")

        with get_database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT role_id
                    FROM auth.roles
                    WHERE role_code = %s;
                    """,
                    (role_code,),
                )
                role = cursor.fetchone()

                if role is None:
                    raise ValueError(f"Unknown role: {role_code}")

                cursor.execute(
                    """
                    SELECT
                        EXISTS (
                            SELECT 1
                            FROM auth.organizations
                            WHERE organization_id = %s
                              AND is_active = TRUE
                        ),
                        EXISTS (
                            SELECT 1
                            FROM auth.users
                            WHERE user_id = %s
                              AND is_active = TRUE
                        );
                    """,
                    (organization_id, user_id),
                )
                organization_active, user_active = cursor.fetchone()

                if not organization_active:
                    raise ValueError(
                        "Organization does not exist or is inactive."
                    )

                if not user_active:
                    raise ValueError("User does not exist or is inactive.")

                cursor.execute(
                    """
                    INSERT INTO auth.organization_memberships (
                        organization_id,
                        user_id,
                        role_id
                    )
                    VALUES (%s, %s, %s)
                    RETURNING membership_id, organization_id, user_id,
                              role_id, is_active, created_at;
                    """,
                    (organization_id, user_id, role[0]),
                )
                row = cursor.fetchone()

        return {
            "membership_id": row[0],
            "organization_id": row[1],
            "user_id": row[2],
            "role_id": row[3],
            "is_active": row[4],
            "created_at": row[5],
            "role_code": role_code,
        }

    @staticmethod
    def get_user_memberships(user_id: int) -> list[dict]:
        if (
            isinstance(user_id, bool)
            or not isinstance(user_id, int)
            or user_id <= 0
        ):
            raise ValueError("A valid user_id is required.")

        with get_database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        m.membership_id,
                        m.organization_id,
                        o.name,
                        o.slug,
                        m.user_id,
                        r.role_code,
                        m.is_active,
                        m.created_at
                    FROM auth.organization_memberships m
                    JOIN auth.organizations o
                        ON o.organization_id = m.organization_id
                    JOIN auth.roles r
                        ON r.role_id = m.role_id
                    WHERE m.user_id = %s
                    ORDER BY m.created_at, m.membership_id;
                    """,
                    (user_id,),
                )
                rows = cursor.fetchall()

        return [
            {
                "membership_id": row[0],
                "organization_id": row[1],
                "organization_name": row[2],
                "organization_slug": row[3],
                "user_id": row[4],
                "role_code": row[5],
                "is_active": row[6],
                "created_at": row[7],
            }
            for row in rows
        ]


    @staticmethod
    def create_refresh_session(
        user_id: int,
        organization_id: int,
        token_jti: str,
        expires_at: datetime,
    ) -> dict:
        if not isinstance(token_jti, str):
            raise ValueError("A valid token_jti is required.")

        try:
            token_jti = str(UUID(token_jti))
        except ValueError as exc:
            raise ValueError("A valid token_jti is required.") from exc

        if expires_at.tzinfo is None or expires_at.utcoffset() is None:
            raise ValueError("expires_at must include a timezone.")

        if expires_at <= datetime.now(timezone.utc):
            raise ValueError("Refresh token expiration must be in the future.")

        with get_database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO auth.refresh_tokens (
                        user_id,
                        organization_id,
                        token_jti,
                        expires_at
                    )
                    SELECT %s, %s, %s, %s
                    WHERE EXISTS (
                        SELECT 1
                        FROM auth.organization_memberships m
                        JOIN auth.users u ON u.user_id = m.user_id
                        JOIN auth.organizations o
                            ON o.organization_id = m.organization_id
                        WHERE m.user_id = %s
                          AND m.organization_id = %s
                          AND m.is_active = TRUE
                          AND u.is_active = TRUE
                          AND o.is_active = TRUE
                    )
                    RETURNING refresh_token_id, user_id, organization_id,
                              token_jti, expires_at, revoked_at, created_at;
                    """,
                    (
                        user_id,
                        organization_id,
                        token_jti,
                        expires_at,
                        user_id,
                        organization_id,
                    ),
                )
                row = cursor.fetchone()

                if row is None:
                    raise ValueError(
                        "No active organization membership exists for this user."
                    )

        return {
            "refresh_token_id": row[0],
            "user_id": row[1],
            "organization_id": row[2],
            "token_jti": str(row[3]),
            "expires_at": row[4],
            "revoked_at": row[5],
            "created_at": row[6],
        }

    @staticmethod
    def get_active_refresh_session(token_jti: str) -> dict | None:
        try:
            token_jti = str(UUID(token_jti))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError("A valid token_jti is required.") from exc

        with get_database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        rt.refresh_token_id,
                        rt.user_id,
                        rt.organization_id,
                        rt.token_jti,
                        rt.expires_at,
                        rt.created_at
                    FROM auth.refresh_tokens rt
                    JOIN auth.users u ON u.user_id = rt.user_id
                    JOIN auth.organizations o
                        ON o.organization_id = rt.organization_id
                    JOIN auth.organization_memberships m
                        ON m.user_id = rt.user_id
                       AND m.organization_id = rt.organization_id
                    WHERE rt.token_jti = %s
                      AND rt.revoked_at IS NULL
                      AND rt.expires_at > CURRENT_TIMESTAMP
                      AND u.is_active = TRUE
                      AND o.is_active = TRUE
                      AND m.is_active = TRUE;
                    """,
                    (token_jti,),
                )
                row = cursor.fetchone()

        if row is None:
            return None

        return {
            "refresh_token_id": row[0],
            "user_id": row[1],
            "organization_id": row[2],
            "token_jti": str(row[3]),
            "expires_at": row[4],
            "created_at": row[5],
        }

    @staticmethod
    def revoke_refresh_session(token_jti: str) -> bool:
        try:
            token_jti = str(UUID(token_jti))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError("A valid token_jti is required.") from exc

        with get_database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE auth.refresh_tokens
                    SET revoked_at = CURRENT_TIMESTAMP
                    WHERE token_jti = %s
                      AND revoked_at IS NULL
                    RETURNING refresh_token_id;
                    """,
                    (token_jti,),
                )
                row = cursor.fetchone()

        return row is not None
