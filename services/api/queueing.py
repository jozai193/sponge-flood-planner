"""Durable PostgreSQL-backed dispatch and stale RQ job reconciliation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from redis import Redis
from redis.exceptions import RedisError
from rq import Queue
from sqlalchemy import select

from services.api.database import Resource, Session, update_resource
from services.api.settings import settings


def _job_spec(row: Resource) -> tuple[str, tuple, int]:
    if row.kind == "neighbourhood":
        return "services.api.jobs.prepare_job", (row.id, row.payload["request"]), 600
    if row.kind == "enrichment":
        return (
            "services.geodata.enrichment.enrichment_job",
            (row.id, row.bundle_id or row.payload["bundle_id"], row.payload["request"]),
            3000,
        )
    raise ValueError(f"Resource {row.id} is not a queued job")


def ensure_enqueued(resource_id: str) -> bool:
    """Ensure a durable queued row has one corresponding RQ job."""
    with Session() as db:
        row = db.get(Resource, resource_id)
        if row is None or row.status not in {"queued", "running"}:
            return False
        function, args, timeout = _job_spec(row)

    connection = Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)
    lock_key = f"sponge:dispatch:{resource_id}"
    if not connection.set(lock_key, "1", nx=True, ex=30):
        return False
    try:
        queue = Queue("prepare", connection=connection)
        job = queue.fetch_job(resource_id)
        if job is not None:
            status = job.get_status(refresh=True)
            if status in {"queued", "started", "deferred", "scheduled"}:
                return False
            if status in {"failed", "stopped", "canceled"}:
                update_resource(resource_id, "failed", stage="queue_failed", error="Background job failed")
                return False
            if status == "finished":
                update_resource(
                    resource_id,
                    "failed",
                    stage="commit_missing",
                    error="Background work ended without committing its result",
                )
                return False
            job.delete()
        queue.enqueue(
            function,
            *args,
            job_id=resource_id,
            job_timeout=timeout,
            result_ttl=86400,
            failure_ttl=604800,
        )
        return True
    finally:
        try:
            connection.delete(lock_key)
        except RedisError:
            # The job is already durable in RQ. A lock-cleanup outage must not
            # make the API report that dispatch failed.
            pass


def reconcile_jobs() -> dict[str, int]:
    """Redeliver queued rows and fail abandoned running rows."""
    cutoff = datetime.now(UTC) - timedelta(seconds=settings.job_stale_seconds)
    with Session() as db:
        rows = list(db.scalars(select(Resource).where(Resource.status.in_(["queued", "running"]))))

    report = {"inspected": len(rows), "dispatched": 0, "failed": 0}
    for row in rows:
        if row.status == "queued":
            if ensure_enqueued(row.id):
                report["dispatched"] += 1
            continue
        if row.updated_at >= cutoff:
            continue
        connection = Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)
        job = Queue("prepare", connection=connection).fetch_job(row.id)
        status = job.get_status(refresh=True) if job is not None else "missing"
        if status not in {"started", "queued", "deferred", "scheduled"}:
            update_resource(
                row.id,
                "failed",
                stage="stale",
                error=f"Background job became stale ({status}); submit the request again",
            )
            report["failed"] += 1
    return report
