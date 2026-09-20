import json
from datetime import UTC, datetime, timedelta
from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile
from fastapi.testclient import TestClient

from services.api import main
from services.api.client_identity import client_ip


def terrain_source():
    return json.dumps({
        "title": "Fixture terrain",
        "attribution": "Test survey",
        "observed_at": "2026-09-20T00:00:00Z",
        "horizontal_crs": "EPSG:4326",
        "vertical_datum": "EGM96",
        "license": "Test data",
        "provenance": "surveyed",
        "surface_type": "bare_earth",
    })


def test_api_responses_include_baseline_security_headers():
    response = TestClient(main.app).get("/api/v1/health")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["version"] == main.settings.app_version


def test_untrusted_host_is_rejected():
    response = TestClient(main.app).get(
        "/api/v1/health", headers={"host": "untrusted.example"}
    )

    assert response.status_code == 400


def test_session_creation_is_rate_limited_before_database_work(monkeypatch):
    class Pipeline:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def incr(self, *_):
            return self

        def expire(self, *_):
            return self

        def execute(self):
            return [2, True]

    class RedisConnection:
        def pipeline(self, **_):
            return Pipeline()

    monkeypatch.setattr(main.Redis, "from_url", lambda *_args, **_kwargs: RedisConnection())
    monkeypatch.setattr(main.settings, "session_limit_per_hour", 1)

    response = TestClient(main.app).post("/api/v1/sessions")

    assert response.status_code == 429
    assert response.json() == {"detail": "Public session limit reached; retry later"}


def test_session_creation_returns_structured_503_when_redis_is_unavailable(monkeypatch):
    from redis.exceptions import ConnectionError

    monkeypatch.setattr(
        main.Redis,
        "from_url",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ConnectionError("offline")),
    )
    monkeypatch.setattr(main.time, "sleep", lambda *_: None)

    response = TestClient(main.app).post("/api/v1/sessions")

    assert response.status_code == 503
    assert response.json() == {"detail": "Session service temporarily unavailable"}


def test_streamed_request_is_rejected_before_json_parsing(monkeypatch):
    monkeypatch.setattr(main.settings, "max_request_body_bytes", 8)
    main.app.dependency_overrides[main.identity] = lambda: "test-session"
    try:
        response = TestClient(main.app).post(
            "/api/v1/geocode",
            content=(chunk for chunk in [b'{"query":', b'"too long"}']),
            headers={"content-type": "application/json"},
        )
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 413
    assert response.json() == {"detail": "Request body is too large"}


def test_forwarded_client_is_used_only_for_configured_proxy(monkeypatch):
    from starlette.requests import Request

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/sessions",
        "headers": [(b"x-forwarded-for", b"203.0.113.8")],
        "client": ("10.0.0.4", 1234),
        "server": ("testserver", 80),
        "scheme": "http",
        "query_string": b"",
    }
    request = Request(scope)
    monkeypatch.setattr(main.settings, "trusted_proxy_cidrs", "")
    assert client_ip(request) == "10.0.0.4"
    monkeypatch.setattr(main.settings, "trusted_proxy_cidrs", "10.0.0.0/24")
    assert client_ip(request) == "203.0.113.8"


def test_expired_session_is_rejected(monkeypatch):
    class Database:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def scalar(self, *_):
            return type("Expired", (), {
                "id": "expired",
                "expires_at": datetime.now(UTC) - timedelta(seconds=1),
            })()

    monkeypatch.setattr(main, "Session", lambda: Database())
    with pytest.raises(HTTPException) as error:
        main.identity("Bearer expired-token")
    assert error.value.status_code == 401
    assert error.value.detail == "Session expired"


def test_oversized_terrain_upload_removes_staged_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "EVIDENCE", tmp_path)
    monkeypatch.setattr(main, "MAX_TERRAIN_UPLOAD_BYTES", 1)
    monkeypatch.setattr(main, "bundle_access", lambda *_: tmp_path)
    upload = UploadFile(filename="terrain.tif", file=BytesIO(b"12"))

    with pytest.raises(HTTPException) as error:
        main.terrain_import("a" * 64, upload, terrain_source(), "test-session")

    assert error.value.status_code == 413
    assert list(tmp_path.iterdir()) == []


def test_invalid_terrain_upload_removes_staged_evidence(tmp_path, monkeypatch):
    from services.geodata import terrain_import as terrain_module

    monkeypatch.setattr(main, "EVIDENCE", tmp_path)
    monkeypatch.setattr(main, "bundle_access", lambda *_: tmp_path)
    monkeypatch.setattr(terrain_module, "import_terrain", lambda *_: (_ for _ in ()).throw(ValueError("invalid raster")))
    upload = UploadFile(filename="terrain.tif", file=BytesIO(b"not a raster"))

    with pytest.raises(HTTPException) as error:
        main.terrain_import("a" * 64, upload, terrain_source(), "test-session")

    assert error.value.status_code == 422
    assert list(tmp_path.iterdir()) == []
