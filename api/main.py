"""FastAPI app entrypoint (§6.1)."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.db import init_db
from api.routers.sessions import router as sessions_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Cadence API", version="0.1.0", lifespan=lifespan)

# Dev-only: allow the local Next.js dev server to call this API directly.
# Production serves the frontend from an allowlisted origin, not "*".
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
