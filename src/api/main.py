from fastapi import FastAPI
from src.api.routers import health, database

app = FastAPI(
    title="Hazina API",
    description="REST API for the Hazina Financial Transactions Pipeline.",
    version="2.0.0",
)

app.include_router(health.router)
app.include_router(database.router)