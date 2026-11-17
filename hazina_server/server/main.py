from fastapi import FastAPI
from server.routers import health, database, sources, mappings
from server.routers import pipeline, auth, admin


app = FastAPI(
    title="Hazina API",
    description="REST API for the Hazina Financial Transactions Pipeline.",
    version="2.0.0",
)

app.include_router(health.router)
app.include_router(database.router)
app.include_router(sources.router)
app.include_router(mappings.router)
app.include_router(pipeline.router)
app.include_router(auth.router)
app.include_router(admin.router)