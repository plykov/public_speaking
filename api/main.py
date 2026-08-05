"""FastAPI app entrypoint (§6.1)."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.db import init_db
from api.routers.admin import router as admin_router
from api.routers.billing import router as billing_router
from api.routers.feedback import router as feedback_router
from api.routers.push import router as push_router
from api.routers.sessions import router as sessions_router
from api.routers.users import catalog_router as l1_catalog_router
from api.routers.users import router as users_router


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
app.include_router(users_router)
app.include_router(l1_catalog_router)
app.include_router(feedback_router)
app.include_router(admin_router)
app.include_router(billing_router)
app.include_router(push_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
