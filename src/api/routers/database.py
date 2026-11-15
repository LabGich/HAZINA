from fastapi import APIRouter, HTTPException
from psycopg import Error

from src.database.connection import get_database_connection

router = APIRouter()

@router.get("/health/database", tags=["Health"])
def database_health_check():
    connection = None

    try:
        connection = get_database_connection()

        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone

        return{
            "status": "healthy",
            "database": "connected",
        }

    except(Error, ValueError):
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "database": "unavailable"
            },
        )

    finally:
        if connection is not None:
            connection.close()