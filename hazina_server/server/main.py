
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.routers import health, database, sources, mappings
from server.routers import pipeline, auth, admin


app = FastAPI(
    title="Hazina API",
    description="REST API for the Hazina Financial Transactions Pipeline.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(database.router)
app.include_router(sources.router)
app.include_router(mappings.router)
app.include_router(pipeline.router)
app.include_router(auth.router)
app.include_router(admin.router)
