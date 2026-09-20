"""Reference-safe expiry for private session metadata and stored artifacts."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select

from services.api.database import Resource, Session, UserSession
from services.geodata.enrichment import EVIDENCE
from services.geodata.prepare import ROOT


def purge_expired(now: datetime | None = None) -> dict[str, int]:
    now = now or datetime.now(UTC)
    with Session.begin() as db:
        session_ids = list(db.scalars(select(UserSession.id).where(UserSession.expires_at <= now)))
        resources = (
            list(db.scalars(select(Resource).where(Resource.session_id.in_(session_ids))))
            if session_ids
            else []
        )
        resource_ids = [row.id for row in resources]
        bundle_ids = {row.bundle_id for row in resources if row.bundle_id}
        if session_ids:
            db.execute(delete(Resource).where(Resource.session_id.in_(session_ids)))
            db.execute(delete(UserSession).where(UserSession.id.in_(session_ids)))

    evidence_removed = 0
    for resource_id in resource_ids:
        path = EVIDENCE / resource_id
        if path.is_dir():
            shutil.rmtree(path)
            evidence_removed += 1

    bundles_removed = 0
    with Session() as db:
        for bundle_id in bundle_ids:
            references = db.scalar(
                select(func.count()).select_from(Resource).where(Resource.bundle_id == bundle_id)
            )
            path = ROOT / bundle_id
            if not references and path.is_dir():
                shutil.rmtree(path)
                bundles_removed += 1

    staging_removed = 0
    stale_before = now - timedelta(days=1)
    staging_root = ROOT / ".staging"
    if staging_root.is_dir():
        for path in staging_root.iterdir():
            modified = datetime.fromtimestamp(path.stat().st_mtime, UTC)
            if modified < stale_before:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                staging_removed += 1

    return {
        "sessions": len(session_ids),
        "resources": len(resource_ids),
        "bundles": bundles_removed,
        "evidence": evidence_removed,
        "staging": staging_removed,
    }
