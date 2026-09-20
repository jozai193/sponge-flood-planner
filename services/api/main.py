from __future__ import annotations

import hashlib
import json
import logging
import secrets
import shutil
import time
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from redis import Redis
from redis.exceptions import RedisError
from rq import Queue, Worker
from sqlalchemy import select, text
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware

from services.api.body_limit import RequestBodyLimitMiddleware
from services.api.client_identity import client_ip
from services.api.contracts import CPUReferenceRequest, Design, PlanningRequest, PrepareRequest, Storm
from services.api.data_admission import assess_scenario_data
from services.api.database import Resource, Session, UserSession, engine
from services.api.queueing import ensure_enqueued
from services.api.scenario_admission import assess_scenario
from services.api.scenario_contract import ScenarioSpecV2
from services.api.settings import settings
from services.geodata.enrichment import CAPABILITIES, EVIDENCE, ApplyEvidenceRequest, EnrichmentRequest
from services.geodata.geocoding import coordinate_result, search_places
from services.geodata.prepare import ROOT
from services.geodata.providers import usgs_products

MAX_TERRAIN_UPLOAD_BYTES = 100_000_000
logger = logging.getLogger("sponge.api")


def redis_connection():
    return Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)


production = settings.environment.lower() == "production"
app = FastAPI(
    title="SPONGE",
    version=settings.app_version,
    docs_url=None if production else "/docs",
    redoc_url=None if production else "/redoc",
)
trusted_hosts = [host.strip() for host in settings.trusted_hosts.split(",") if host.strip()]
if trusted_hosts and trusted_hosts != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization", "Idempotency-Key"],
)
app.add_middleware(RequestBodyLimitMiddleware)


@app.middleware("http")
async def secure_responses(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    if production:
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https:; connect-src 'self' https:; worker-src 'self' blob:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'",
        )
    return response


def identity(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Session required")
    digest = hashlib.sha256(authorization[7:].encode()).hexdigest()
    with Session() as db:
        user = db.scalar(select(UserSession).where(UserSession.token_hash == digest))
        if user is None:
            raise HTTPException(401, "Invalid session")
        if user.expires_at <= datetime.now(UTC):
            raise HTTPException(401, "Session expired")
        return user.id


def resource(resource_id: str, session_id: str):
    with Session() as db:
        row = db.get(Resource, resource_id)
        if row is None or (row.session_id is not None and row.session_id != session_id):
            raise HTTPException(404, "Resource not found")
        return row


def bundle_access(bundle_id: str, session_id: str):
    if len(bundle_id) != 64 or any(c not in "0123456789abcdef" for c in bundle_id):
        raise HTTPException(404, "Bundle not found")
    with Session() as db:
        row = db.scalar(
            select(Resource)
            .where(
                Resource.bundle_id == bundle_id,
                Resource.status == "completed",
                (Resource.session_id.is_(None)) | (Resource.session_id == session_id),
            )
            .limit(1)
        )
        folder = ROOT / bundle_id
        if row is not None:
            if not (folder / "manifest.json").is_file():
                raise HTTPException(503, "Bundle metadata exists but artifacts are unavailable")
            return folder
    raise HTTPException(404, "Bundle not found")


def enqueue_job(resource_id: str):
    for attempt in range(3):
        try:
            ensure_enqueued(resource_id)
            return
        except RedisError as exc:
            if attempt == 2:
                raise HTTPException(503, "Background queue unavailable; retry shortly") from exc
            time.sleep(0.1 * (attempt + 1))
        except Exception as exc:
            raise HTTPException(503, "Background queue unavailable; retry shortly") from exc


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "version": settings.app_version}


@app.get("/api/v1/ready")
def ready():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    connection = redis_connection()
    try:
        connection.ping()
        queue = Queue("prepare", connection=connection)
        workers = Worker.all(queue=queue)
    except RedisError as exc:
        raise HTTPException(503, "Queue unavailable") from exc
    if not workers:
        raise HTTPException(503, "Preparation worker unavailable")
    return {
        "database": "ready",
        "queue": "ready",
        "worker": "ready",
        "planner": "browser_physics_search",
        "runtime_llm_required": False,
    }


@app.post("/api/v1/sessions")
def new_session(request: Request):
    client = client_ip(request)
    rate_key = (
        "sponge:sessions:" + hashlib.sha256(client.encode()).hexdigest() + ":" + str(int(time.time() // 3600))
    )
    for attempt in range(3):
        try:
            connection = redis_connection()
            with connection.pipeline(transaction=True) as pipe:
                pipe.incr(rate_key)
                pipe.expire(rate_key, 3700)
                count, _ = pipe.execute()
            break
        except RedisError as exc:
            if attempt == 2:
                raise HTTPException(503, "Session service temporarily unavailable") from exc
            time.sleep(0.1 * (attempt + 1))
    if count > settings.session_limit_per_hour:
        raise HTTPException(429, "Public session limit reached; retry later")
    token = secrets.token_urlsafe(32)
    session_id = str(uuid4())
    expires_at = datetime.now(UTC) + timedelta(hours=settings.session_ttl_hours)
    with Session.begin() as db:
        db.add(
            UserSession(
                id=session_id, token_hash=hashlib.sha256(token.encode()).hexdigest(), expires_at=expires_at
            )
        )
    return {"session_id": session_id, "token": token, "revision": 0, "expires_at": expires_at.isoformat()}


@app.get("/api/v1/examples")
def examples():
    with Session() as db:
        return [
            {"id": r.id, **r.payload} for r in db.scalars(select(Resource).where(Resource.kind == "sample"))
        ]


@app.post("/api/v1/geocode")
def geocode(body: dict, session_id=Depends(identity)):
    query = str(body.get("query", ""))[:200].strip()
    if not query:
        raise HTTPException(422, "Enter an address")
    try:
        coordinates = coordinate_result(query)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    if coordinates is not None:
        return coordinates
    region = str(body.get("region", ""))[:100].strip()
    if region:
        query += ", " + region
    connection = redis_connection()
    try:
        allowed = connection.set("sponge:geocode:global", 1, nx=True, ex=2)
    except RedisError as exc:
        raise HTTPException(503, "Search rate limiter unavailable") from exc
    if not allowed:
        raise HTTPException(429, "Please wait before searching again")
    return search_places(
        query,
        nominatim_url=settings.nominatim_url,
        photon_url=settings.photon_url,
        allow_request=lambda provider: bool(
            connection.set("sponge:geocode:provider:" + provider, 1, nx=True, px=1100)
        ),
    )


@app.post("/api/v1/coverage")
def coverage(body: PrepareRequest, session_id=Depends(identity)):
    delta = body.extent_m / 111000
    products, _ = usgs_products(
        (body.longitude - delta, body.latitude - delta, body.longitude + delta, body.latitude + delta)
    )
    return {
        "usgs_1m_products": len(products),
        "terrarium_status": "provider_configured_not_verified_at_location",
        "supported_latitude_range": [-80, 80],
        "hydraulic_network": "not_connected",
        "missing_inputs": [
            "verified parcel eligibility",
            "soil calibration",
            "building valuations and floor levels",
            "boundary assessment",
        ],
    }


@app.post("/api/v1/scenarios/assess")
def scenario_assessment(body: ScenarioSpecV2, session_id=Depends(identity)):
    return assess_scenario(body)


@app.post("/api/v1/scenarios/assess-data")
def scenario_data_assessment(body: ScenarioSpecV2, session_id=Depends(identity)):
    # Resolve through existing ownership checks; never accept client-supplied quality claims.
    folder = bundle_access(body.domain.bundle_id or "", session_id)
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    return {"engine": assess_scenario(body), "data": assess_scenario_data(body, manifest)}


@app.post("/api/v1/neighbourhoods", status_code=202)
def new_neighbourhood(
    body: PrepareRequest, session_id=Depends(identity), idempotency_key: str | None = Header(default=None)
):
    request = body.model_dump()
    resource_id = None
    response_status = "queued"
    with Session.begin() as db:
        existing = list(
            db.scalars(
                select(Resource).where(Resource.session_id == session_id, Resource.kind == "neighbourhood")
            )
        )
        if idempotency_key:
            for row in existing:
                if row.payload.get("idempotency_key") == idempotency_key:
                    if row.payload["request"] != request:
                        raise HTTPException(409, "Idempotency key reused with different input")
                    resource_id = row.id
                    response_status = row.status
                    break
        for row in existing:
            if resource_id is not None:
                break
            if row.status in ("queued", "running"):
                if row.payload.get("request") == request:
                    resource_id = row.id
                    response_status = row.status
                    break
                raise HTTPException(
                    429,
                    "Another neighbourhood is preparing. Wait for it to finish before selecting a different location.",
                )
        if resource_id is None:
            resource_id = str(uuid4())
            db.add(
                Resource(
                    id=resource_id,
                    session_id=session_id,
                    kind="neighbourhood",
                    status="queued",
                    payload={"request": request, "idempotency_key": idempotency_key},
                )
            )
    enqueue_job(resource_id)
    return {"id": resource_id, "status": response_status}


@app.get("/api/v1/neighbourhoods/{resource_id}")
def get_neighbourhood(resource_id: str, session_id=Depends(identity)):
    row = resource(resource_id, session_id)
    if row.status == "queued":
        try:
            ensure_enqueued(row.id)
        except Exception as exc:  # noqa: BLE001 - status reads remain available during queue outages.
            logger.warning("Queued job dispatch delayed for %s: %s", row.id, type(exc).__name__)
    result = {"id": row.id, "status": row.status, **row.payload}
    if row.status == "queued":
        try:
            queue = Queue("prepare", connection=redis_connection())
            result["worker_available"] = bool(Worker.all(queue=queue))
        except RedisError:
            result["worker_available"] = False
    return result


@app.get("/api/v1/bundles/{bundle_id}")
def get_bundle(bundle_id: str, session_id=Depends(identity)):
    return json.loads((bundle_access(bundle_id, session_id) / "manifest.json").read_text())


@app.get("/api/v1/bundles/{bundle_id}/arrays/{name}")
def get_array(bundle_id: str, name: str, session_id=Depends(identity)):
    if name not in ("z", "solid", "rain_weights", "roughness", "soil_capacity", "infiltration"):
        raise HTTPException(404, "Array not found")
    return FileResponse(
        bundle_access(bundle_id, session_id) / f"{name}.bin", media_type="application/octet-stream"
    )


@app.get("/api/v1/bundles/{bundle_id}/context")
def get_context(bundle_id: str, session_id=Depends(identity)):
    import subprocess

    from services.geodata.context_service import bounded_context

    folder = bundle_access(bundle_id, session_id)
    try:
        return bounded_context(json.loads((folder / "manifest.json").read_text()))
    except (subprocess.SubprocessError, RuntimeError, OSError, ValueError):
        raise HTTPException(503, "Landscape acquisition unavailable or timed out; retry shortly")


@app.get("/api/v1/bundles/{bundle_id}/audit")
def get_audit(bundle_id: str, session_id=Depends(identity)):
    from services.geodata.audit import audit_bundle

    return audit_bundle(bundle_access(bundle_id, session_id))


@app.get("/api/v1/bundles/{bundle_id}/design-storms/noaa")
def get_noaa_design_storm(
    bundle_id: str,
    duration_minutes: int = Query(60),
    return_period_years: int = Query(100),
    distribution: Literal["uniform", "centered", "front_loaded", "rear_loaded"] = Query("centered"),
    antecedent_saturation: float = Query(0.25, ge=0, le=1),
    session_id=Depends(identity),
):
    """Create an auditable point-frequency storm for the bundle location."""
    from services.geodata.noaa_atlas14 import design_storm

    folder = bundle_access(bundle_id, session_id)
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    try:
        longitude, latitude = manifest["location"]
        return design_storm(
            latitude=latitude,
            longitude=longitude,
            label=manifest.get("label", bundle_id),
            duration_minutes=duration_minutes,
            return_period_years=return_period_years,
            distribution=distribution,
            antecedent_saturation=antecedent_saturation,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(422, str(exc)[:600]) from exc
    except Exception as exc:
        raise HTTPException(
            503,
            "NOAA Atlas 14 is unavailable for this location; retry later or use a sourced rainfall import.",
        ) from exc


@app.post("/api/v1/bundles/{bundle_id}/enrichment", status_code=202)
def enrich(bundle_id: str, body: EnrichmentRequest, session_id=Depends(identity)):
    bundle_access(bundle_id, session_id)
    with Session.begin() as db:
        existing = db.scalar(
            select(Resource).where(
                Resource.session_id == session_id,
                Resource.kind == "enrichment",
                Resource.status.in_(["queued", "running"]),
            )
        )
        if existing:
            raise HTTPException(429, "An enrichment job is already running")
        job_id = str(uuid4())
        request = body.model_dump(mode="json")
        db.add(
            Resource(
                id=job_id,
                session_id=session_id,
                bundle_id=bundle_id,
                kind="enrichment",
                status="queued",
                payload={"bundle_id": bundle_id, "request": request, "results": {}},
            )
        )
    enqueue_job(job_id)
    return {"id": job_id, "status": "queued"}


@app.get("/api/v1/enrichment/{job_id}")
def enrichment_status(job_id: str, session_id=Depends(identity)):
    row = resource(job_id, session_id)
    if row.kind != "enrichment":
        raise HTTPException(404, "Enrichment not found")
    if row.status == "queued":
        try:
            ensure_enqueued(row.id)
        except Exception as exc:  # noqa: BLE001 - status reads remain available during queue outages.
            logger.warning("Queued enrichment dispatch delayed for %s: %s", row.id, type(exc).__name__)
    return {"id": row.id, "status": row.status, **row.payload}


@app.get("/api/v1/bundles/{bundle_id}/enrichment")
def list_enrichment(bundle_id: str, session_id=Depends(identity)):
    bundle_access(bundle_id, session_id)
    with Session() as db:
        return [
            {"id": r.id, "status": r.status, **r.payload}
            for r in db.scalars(
                select(Resource)
                .where(
                    Resource.session_id == session_id,
                    Resource.bundle_id == bundle_id,
                    Resource.kind == "enrichment",
                )
                .order_by(Resource.created_at.desc())
                .limit(10)
            )
        ]


@app.get("/api/v1/enrichment/{job_id}/{capability}")
def enrichment_data(job_id: str, capability: str, session_id=Depends(identity)):
    row = resource(job_id, session_id)
    if row.kind != "enrichment" or capability not in CAPABILITIES:
        raise HTTPException(404, "Layer not found")
    if row.payload.get("results", {}).get(capability, {}).get("status") not in ("available", "catalog_only"):
        raise HTTPException(409, "Layer is not available")
    return FileResponse(EVIDENCE / row.id / f"{capability}.json", media_type="application/json")


@app.post("/api/v1/enrichment/{job_id}/apply")
def apply_enrichment(job_id: str, body: ApplyEvidenceRequest, session_id=Depends(identity)):
    row = resource(job_id, session_id)
    if row.kind != "enrichment":
        raise HTTPException(404, "Enrichment not found")
    for capability, selected in [("buildings", body.buildings), ("landcover", body.landcover)]:
        if selected and row.payload.get("results", {}).get(capability, {}).get("status") != "available":
            raise HTTPException(409, f"{capability} is not available")
    from services.geodata.merge import apply_evidence

    try:
        manifest, report = apply_evidence(row.payload["bundle_id"], row.id, body.buildings, body.landcover)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    with Session.begin() as db:
        db.add(
            Resource(
                id=str(uuid4()),
                session_id=session_id,
                bundle_id=manifest["bundle_id"],
                kind="neighbourhood",
                status="completed",
                payload={"bundle_id": manifest["bundle_id"], "parent_bundle_id": row.payload["bundle_id"]},
            )
        )
    return {"bundle_id": manifest["bundle_id"], "reconciliation": report}


@app.post("/api/v1/bundles/{bundle_id}/imports")
async def import_survey(bundle_id: str, request: Request, session_id=Depends(identity)):
    bundle_access(bundle_id, session_id)
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > 10_000_000:
            raise HTTPException(413, "Survey exceeds 10 MB")
    from services.geodata.imports import validate_import

    try:
        survey = validate_import(json.loads(raw))
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise HTTPException(422, str(exc)[:1000])
    job_id = str(uuid4())
    folder = EVIDENCE / job_id
    folder.mkdir(parents=True)
    payload = survey.model_dump(mode="json")
    (folder / "survey.json").write_text(json.dumps(payload, allow_nan=False), encoding="utf-8")
    with Session.begin() as db:
        db.add(
            Resource(
                id=job_id,
                session_id=session_id,
                bundle_id=bundle_id,
                kind="survey",
                status="completed",
                payload={
                    "bundle_id": bundle_id,
                    "kind": survey.kind,
                    "source": payload["source"],
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "use": "validated_structure_not_calibrated",
                },
            )
        )
    return {
        "id": job_id,
        "kind": survey.kind,
        "status": "imported",
        "use": "validated_structure_not_calibrated",
    }


@app.get("/api/v1/import-formats")
def import_formats():
    from services.geodata.imports import (
        DrainageSurvey,
        RainfallSurvey,
        SurveySource,
        TerrainSource,
        VectorSurvey,
    )

    return {
        model.__name__: model.model_json_schema()
        for model in [SurveySource, TerrainSource, DrainageSurvey, RainfallSurvey, VectorSurvey]
    }


@app.get("/api/v1/bundles/{bundle_id}/imports")
def list_surveys(bundle_id: str, session_id=Depends(identity)):
    bundle_access(bundle_id, session_id)
    with Session() as db:
        return [
            {"id": r.id, **r.payload}
            for r in db.scalars(
                select(Resource).where(
                    Resource.session_id == session_id,
                    Resource.bundle_id == bundle_id,
                    Resource.kind == "survey",
                )
            )
        ]


@app.get("/api/v1/imports/{survey_id}")
def get_survey(survey_id: str, session_id=Depends(identity)):
    row = resource(survey_id, session_id)
    if row.kind != "survey":
        raise HTTPException(404, "Survey not found")
    return FileResponse(EVIDENCE / row.id / "survey.json", media_type="application/json")


@app.post("/api/v1/bundles/{bundle_id}/terrain-import")
def terrain_import(
    bundle_id: str, file: UploadFile = File(...), source: str = Form(...), session_id=Depends(identity)
):
    bundle_access(bundle_id, session_id)
    from services.geodata.imports import TerrainSource
    from services.geodata.terrain_import import import_terrain

    try:
        metadata = TerrainSource.model_validate_json(source)
    except ValueError as exc:
        raise HTTPException(422, str(exc)[:600])
    folder = EVIDENCE / str(uuid4())
    folder.mkdir(parents=True)
    path = folder / "terrain.tif"
    size = 0
    try:
        with path.open("wb") as output:
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_TERRAIN_UPLOAD_BYTES:
                    raise HTTPException(413, "Terrain upload exceeds 100 MB")
                output.write(chunk)
        manifest = import_terrain(bundle_id, path, metadata.model_dump(mode="json"))
    except HTTPException:
        shutil.rmtree(folder, ignore_errors=True)
        raise
    except Exception as exc:
        shutil.rmtree(folder, ignore_errors=True)
        raise HTTPException(422, str(exc)[:600]) from exc
    with Session.begin() as db:
        db.add(
            Resource(
                id=folder.name,
                session_id=session_id,
                bundle_id=manifest["bundle_id"],
                kind="neighbourhood",
                status="completed",
                payload={
                    "bundle_id": manifest["bundle_id"],
                    "parent_bundle_id": bundle_id,
                    "evidence_id": folder.name,
                },
            )
        )
    return {"bundle_id": manifest["bundle_id"]}


@app.get("/api/v1/bundles/{bundle_id}/imagery")
def get_imagery(bundle_id: str, session_id=Depends(identity)):
    from services.geodata.imagery import descriptor

    folder = bundle_access(bundle_id, session_id)
    return descriptor(json.loads((folder / "manifest.json").read_text()))


@app.post("/api/v1/designs/validate")
def validate_design(body: Design, session_id=Depends(identity)):
    return {"valid": True, "cost_minor": sum(x.cost_minor for x in body.interventions)}


@app.post("/api/v1/storms")
def validate_storm(body: Storm, session_id=Depends(identity)):
    from services.api.contracts import content_hash

    return {"storm_id": content_hash(body), "storm": body.model_dump()}


@app.post("/api/v1/planning/propose")
def propose(body: PlanningRequest, session_id=Depends(identity)):
    folder = bundle_access(body.bundle_id, session_id)
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    available = {
        item["id"]
        for item in manifest.get("candidates", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    unknown = set(body.candidate_ids) - available
    if unknown:
        raise HTTPException(422, "Unknown catalogue IDs: " + ", ".join(sorted(unknown)[:10]))
    return {
        "schema": "sponge.proposal.v1",
        "status": "manual_required",
        "provider": None,
        "model": None,
        "evaluated": False,
        "catalogue_ids": body.candidate_ids,
        "constraints": {
            "budget_minor": body.budget_minor,
            "locked_ids": body.locked_ids,
            "excluded_ids": body.excluded_ids,
        },
        "source_references": body.source_references,
        "proposal": None,
        "message": "No live AI provider is configured. Use deterministic browser planning; any future proposal remains unevaluated until the physics search validates it.",
    }


@app.post("/api/v1/bundles/{bundle_id}/cpu-reference")
async def cpu_reference(bundle_id: str, body: CPUReferenceRequest, session_id=Depends(identity)):
    folder = bundle_access(bundle_id, session_id)
    try:
        allowed = redis_connection().set(f"sponge:cpu-reference:{session_id}", 1, nx=True, ex=10)
    except RedisError as exc:
        raise HTTPException(503, "CPU reference rate limiter unavailable") from exc
    if not allowed:
        raise HTTPException(429, "Wait before starting another CPU reference run")
    from services.reference.process_runner import ReferenceBusy, ReferenceTimedOut, run_reference_bounded

    try:
        return await run_in_threadpool(run_reference_bounded, folder, body)
    except ReferenceBusy as exc:
        raise HTTPException(429, str(exc)) from exc
    except ReferenceTimedOut as exc:
        raise HTTPException(504, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc


if settings.web_dist and (settings.web_dist / "index.html").is_file():
    app.mount("/", StaticFiles(directory=settings.web_dist, html=True), name="web")
