"""FastAPI app entrypoint (§6.1)."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.db import init_db
from api.routers.sessions import router as sessions_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Cadence API", version="0.1.0", lifespan=lifespan)
app.include_router(sessions_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
