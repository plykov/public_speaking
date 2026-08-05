"""Operational endpoints. Not user-facing (§6.5 raw-media retention).

`purge-expired-media` stands in for the scheduled job production would
run (§6.1: Celery/Arq beat, or a cron trigger) — this environment has no
scheduler, so it's exposed as an endpoint an operator (or a real cron
job hitting it) can call. There is no auth on this route; before a real
deployment it needs to sit behind an internal-only network boundary or
an admin credential — tracked as a gap, not fixed here since auth is
out of scope for this iteration.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as OrmSession

from api.db import get_db
from api.deps import get_object_store
from api.lifecycle import DEFAULT_RETENTION_DAYS, purge_expired_media
from api.storage import ObjectStore

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/purge-expired-media")
def purge_expired_media_endpoint(
    retention_days: int = DEFAULT_RETENTION_DAYS,
    db: OrmSession = Depends(get_db),
    store: ObjectStore = Depends(get_object_store),
) -> dict[str, int]:
    deleted = purge_expired_media(db, store, retention_days=retention_days)
    db.commit()
    return {"deleted_media_assets": deleted}
