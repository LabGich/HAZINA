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
    def get_active_user_membership(
        email: str,
        organization_slug: str,
    ) -> dict | None:
        email = email.strip().lower()
        organization_slug = organization_slug.strip().lower()

        if not email or not organization_slug:
            raise ValueError(
                "Email and organization slug are required."
            )

        with get_database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        u.user_id,
                        u.email,
                        u.password_hash,
                        u.full_name,
                        u.is_active,
                        u.email_verified,
                        o.organization_id,
                        o.name,
                        o.slug,
                        r.role_code,
                        m.is_active,
                        m.created_at
                    FROM auth.users u
                    JOIN auth.organization_memberships m
                        ON m.user_id = u.user_id
                    JOIN auth.organizations o
                        ON o.organization_id = m.organization_id
                    JOIN auth.roles r
                        ON r.role_id = m.role_id
                    WHERE u.email = %s
                      AND o.slug = %s
                      AND u.is_active = TRUE
                      AND o.is_active = TRUE
                      AND m.is_active = TRUE;
                    """,
                    (email, organization_slug),
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
            "organization_id": row[6],
            "organization_name": row[7],
            "organization_slug": row[8],
            "role_code": row[9],
            "membership_is_active": row[10],
            "membership_created_at": row[11],
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

    # transactional user creation
    @staticmethod
    def create_user_with_membership(
        email: str,
        password_hash: str,
        full_name: str,
        organization_id: int,
        role_code: str,
    ) -> dict:
        email = email.strip().lower() if isinstance(email, str) else ""
        full_name = full_name.strip() if isinstance(full_name, str) else ""
        role_code = role_code.strip().upper() if isinstance(role_code, str) else ""

        if not email or not password_hash or not full_name:
            raise ValueError(
                "Email, password hash, and full name are required."
            )

        if (
            isinstance(organization_id, bool)
            or not isinstance(organization_id, int)
            or organization_id <= 0
        ):
            raise ValueError("A valid organization_id is required.")

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

                role_id = role[0]

                cursor.execute(
                    """
                    SELECT organization_id
                    FROM auth.organizations
                    WHERE organization_id = %s
                      AND is_active = TRUE;
                    """,
                    (organization_id,),
                )

                if cursor.fetchone() is None:
                    raise ValueError(
                        "Organization does not exist or is inactive."
                    )

                cursor.execute(
                    """
                    SELECT user_id, email, full_name, is_active,
                           email_verified
                    FROM auth.users
                    WHERE email = %s
                    FOR UPDATE;
                    """,
                    (email,),
                )
                user = cursor.fetchone()

                if user is None:
                    cursor.execute(
                        """
                        INSERT INTO auth.users (
                            email, password_hash, full_name
                        )
                        VALUES (%s, %s, %s)
                        RETURNING user_id, email, full_name, is_active,
                                  email_verified;
                        """,
                        (email, password_hash, full_name),
                    )
                    user = cursor.fetchone()

                elif not user[3]:
                    raise ValueError("The existing user account is inactive.")

                user_id = user[0]

                cursor.execute(
                    """
                    SELECT membership_id
                    FROM auth.organization_memberships
                    WHERE organization_id = %s
                      AND user_id = %s;
                    """,
                    (organization_id, user_id),
                )

                if cursor.fetchone() is not None:
                    raise ValueError(
                        "User already has a membership in this organization."
                    )

                cursor.execute(
                    """
                    INSERT INTO auth.organization_memberships (
                        organization_id, user_id, role_id
                    )
                    VALUES (%s, %s, %s)
                    RETURNING membership_id, is_active, created_at;
                    """,
                    (organization_id, user_id, role_id),
                )
                membership = cursor.fetchone()

        return {
            "user_id": user[0],
            "email": user[1],
            "full_name": user[2],
            "user_is_active": user[3],
            "email_verified": user[4],
            "organization_id": organization_id,
            "membership_id": membership[0],
            "role_code": role_code,
            "membership_is_active": membership[1],
            "membership_created_at": membership[2],
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
    def list_organization_users(organization_id: int) -> list[dict]:
        if (
            isinstance(organization_id, bool)
            or not isinstance(organization_id, int)
            or organization_id <= 0
        ):
            raise ValueError("A valid organization_id is required.")

        with get_database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        u.user_id,
                        u.email,
                        u.full_name,
                        u.is_active,
                        u.email_verified,
                        m.membership_id,
                        m.is_active,
                        r.role_code,
                        m.created_at
                    FROM auth.organization_memberships m
                    JOIN auth.users u
                        ON u.user_id = m.user_id
                    JOIN auth.roles r
                        ON r.role_id = m.role_id
                    WHERE m.organization_id = %s
                    ORDER BY u.full_name, u.user_id;
                    """,
                    (organization_id,),
                )
                rows = cursor.fetchall()

        return [
            {
                "user_id": row[0],
                "email": row[1],
                "full_name": row[2],
                "user_is_active": row[3],
                "email_verified": row[4],
                "membership_id": row[5],
                "membership_is_active": row[6],
                "role_code": row[7],
                "membership_created_at": row[8],
            }
            for row in rows
        ]


    @staticmethod
    def update_organization_membership(
        organization_id: int,
        user_id: int,
        role_code: str | None = None,
        is_active: bool | None = None,
    ) -> dict | None:
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

        if role_code is None and is_active is None:
            raise ValueError("At least one membership field must be supplied.")

        if role_code is not None:
            if not isinstance(role_code, str) or not role_code.strip():
                raise ValueError("A valid role_code is required.")
            role_code = role_code.strip().upper()

        if is_active is not None and not isinstance(is_active, bool):
            raise ValueError("is_active must be a boolean.")

        with get_database_connection() as connection:
            with connection.cursor() as cursor:
                role_id = None

                if role_code is not None:
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

                    role_id = role[0]

                cursor.execute(
                    """
                    UPDATE auth.organization_memberships
                    SET
                        role_id = COALESCE(%s, role_id),
                        is_active = COALESCE(%s, is_active),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE organization_id = %s
                      AND user_id = %s
                    RETURNING membership_id, organization_id, user_id,
                              role_id, is_active, created_at;
                    """,
                    (role_id, is_active, organization_id, user_id),
                )
                row = cursor.fetchone()

                if row is None:
                    return None

                cursor.execute(
                    """
                    SELECT role_code
                    FROM auth.roles
                    WHERE role_id = %s;
                    """,
                    (row[3],),
                )
                updated_role = cursor.fetchone()[0]

        return {
            "membership_id": row[0],
            "organization_id": row[1],
            "user_id": row[2],
            "role_id": row[3],
            "is_active": row[4],
            "created_at": row[5],
            "role_code": updated_role,
        }


    @staticmethod
    def get_active_user_context(
        user_id: int,
        organization_id: int,
    ) -> dict | None:
        if (
            isinstance(user_id, bool)
            or not isinstance(user_id, int)
            or user_id <= 0
        ):
            raise ValueError("A valid user_id is required.")

        if (
            isinstance(organization_id, bool)
            or not isinstance(organization_id, int)
            or organization_id <= 0
        ):
            raise ValueError("A valid organization_id is required.")

        with get_database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        u.user_id,
                        u.email,
                        u.full_name,
                        u.is_active,
                        u.email_verified,
                        o.organization_id,
                        o.name,
                        o.slug,
                        r.role_code,
                        m.is_active,
                        m.created_at
                    FROM auth.users u
                    JOIN auth.organization_memberships m
                        ON m.user_id = u.user_id
                    JOIN auth.organizations o
                        ON o.organization_id = m.organization_id
                    JOIN auth.roles r
                        ON r.role_id = m.role_id
                    WHERE u.user_id = %s
                      AND o.organization_id = %s
                      AND u.is_active = TRUE
                      AND o.is_active = TRUE
                      AND m.is_active = TRUE;
                    """,
                    (user_id, organization_id),
                )
                row = cursor.fetchone()

        if row is None:
            return None

        return {
            "user_id": row[0],
            "email": row[1],
            "full_name": row[2],
            "is_active": row[3],
            "email_verified": row[4],
            "organization_id": row[5],
            "organization_name": row[6],
            "organization_slug": row[7],
            "role_code": row[8],
            "membership_is_active": row[9],
            "membership_created_at": row[10],
        }

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
                        rt.created_at,
                        u.email,
                        o.slug
                    FROM auth.refresh_tokens rt
                    JOIN auth.users u
                        ON u.user_id = rt.user_id
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
            "email": row[6],
            "organization_slug": row[7],
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

    # Add atomic refresh-token rotation:
    # Concurrent requests using the same old token cannot both rotate it successfully.
    # Expired, revoked, or inactive-user sessions cannot be rotated
    # The old session records the replacement JTI
    # The old and new session changes are committed together

    @staticmethod
    def rotate_refresh_session(
        old_token_jti: str,
        new_token_jti: str,
        new_expires_at: datetime,
    ) -> dict:
        try:
            old_token_jti = str(UUID(old_token_jti))
            new_token_jti = str(UUID(new_token_jti))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError("Valid token JTIs are required.") from exc

        if old_token_jti == new_token_jti:
            raise ValueError("Replacement token must have a new JTI.")

        if (
            new_expires_at.tzinfo is None
            or new_expires_at.utcoffset() is None
        ):
            raise ValueError("Expiration must include a timezone.")

        if new_expires_at <= datetime.now(timezone.utc):
            raise ValueError("Replacement token expiration must be in the future.")

        with get_database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        rt.refresh_token_id,
                        rt.user_id,
                        rt.organization_id
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
                      AND m.is_active = TRUE
                    FOR UPDATE OF rt;
                    """,
                    (old_token_jti,),
                )
                old_session = cursor.fetchone()

                if old_session is None:
                    raise ValueError(
                        "Refresh session is invalid, expired, or revoked."
                    )

                refresh_token_id, user_id, organization_id = old_session

                cursor.execute(
                    """
                    UPDATE auth.refresh_tokens
                    SET revoked_at = CURRENT_TIMESTAMP,
                        replaced_by_jti = %s
                    WHERE refresh_token_id = %s
                      AND revoked_at IS NULL;
                    """,
                    (new_token_jti, refresh_token_id),
                )

                if cursor.rowcount != 1:
                    raise ValueError("Refresh session could not be rotated.")

                cursor.execute(
                    """
                    INSERT INTO auth.refresh_tokens (
                        user_id,
                        organization_id,
                        token_jti,
                        expires_at
                    )
                    VALUES (%s, %s, %s, %s)
                    RETURNING refresh_token_id, user_id, organization_id,
                              token_jti, expires_at, created_at;
                    """,
                    (
                        user_id,
                        organization_id,
                        new_token_jti,
                        new_expires_at,
                    ),
                )
                new_session = cursor.fetchone()

        return {
            "refresh_token_id": new_session[0],
            "user_id": new_session[1],
            "organization_id": new_session[2],
            "token_jti": str(new_session[3]),
            "expires_at": new_session[4],
            "created_at": new_session[5],
            "replaced_token_jti": old_token_jti,
        }

    # one atomic bootstrap functionality to create inital org, initial user, and ADMIN
    # will use the CLI
    @staticmethod
    def create_organization_with_admin(
        organization_name: str,
        organization_slug: str,
        email: str,
        password_hash: str,
        full_name: str,
    ) -> dict:
        organization_name = (
            organization_name.strip()
            if isinstance(organization_name, str)
            else ""
        )
        organization_slug = (
            organization_slug.strip().lower()
            if isinstance(organization_slug, str)
            else ""
        )
        email = email.strip().lower() if isinstance(email, str) else ""
        full_name = full_name.strip() if isinstance(full_name, str) else ""

        if not organization_name or not organization_slug:
            raise ValueError(
                "Organization name and slug are required."
            )

        if not email or not password_hash or not full_name:
            raise ValueError(
                "Admin email, password hash, and full name are required."
            )

        with get_database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT role_id
                    FROM auth.roles
                    WHERE role_code = 'ADMIN';
                    """
                )
                role = cursor.fetchone()

                if role is None:
                    raise ValueError("ADMIN role is not configured.")

                cursor.execute(
                    """
                    INSERT INTO auth.organizations (name, slug)
                    VALUES (%s, %s)
                    RETURNING organization_id, name, slug, is_active,
                              created_at;
                    """,
                    (organization_name, organization_slug),
                )
                organization = cursor.fetchone()

                cursor.execute(
                    """
                    INSERT INTO auth.users (
                        email, password_hash, full_name
                    )
                    VALUES (%s, %s, %s)
                    RETURNING user_id, email, full_name, is_active,
                              email_verified;
                    """,
                    (email, password_hash, full_name),
                )
                user = cursor.fetchone()

                cursor.execute(
                    """
                    INSERT INTO auth.organization_memberships (
                        organization_id,
                        user_id,
                        role_id
                    )
                    VALUES (%s, %s, %s)
                    RETURNING membership_id, is_active, created_at;
                    """,
                    (organization[0], user[0], role[0]),
                )
                membership = cursor.fetchone()

        return {
            "organization_id": organization[0],
            "organization_name": organization[1],
            "organization_slug": organization[2],
            "organization_is_active": organization[3],
            "user_id": user[0],
            "email": user[1],
            "full_name": user[2],
            "user_is_active": user[3],
            "email_verified": user[4],
            "membership_id": membership[0],
            "membership_is_active": membership[1],
            "membership_created_at": membership[2],
            "role_code": "ADMIN",
        }
