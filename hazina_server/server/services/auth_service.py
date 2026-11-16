from hazina_pipeline.database.connection import get_database_connection


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