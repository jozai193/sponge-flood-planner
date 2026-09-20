import os
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from services.api import queueing, retention
from services.api.database import Base, Resource, UserSession


def test_expiry_removes_only_unreferenced_private_artifacts(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(UTC)
    with session.begin() as db:
        db.add_all(
            [
                UserSession(id="expired", token_hash="expired", expires_at=now - timedelta(seconds=1)),
                UserSession(id="alive", token_hash="alive", expires_at=now + timedelta(hours=1)),
            ]
        )
        db.add_all(
            [
                Resource(
                    id="expired-evidence",
                    session_id="expired",
                    bundle_id="shared",
                    kind="survey",
                    status="completed",
                ),
                Resource(
                    id="expired-bundle",
                    session_id="expired",
                    bundle_id="private",
                    kind="neighbourhood",
                    status="completed",
                ),
                Resource(
                    id="alive-bundle",
                    session_id="alive",
                    bundle_id="shared",
                    kind="neighbourhood",
                    status="completed",
                ),
            ]
        )
    bundles = tmp_path / "bundles"
    evidence = tmp_path / "evidence"
    for name in ["shared", "private"]:
        (bundles / name).mkdir(parents=True)
    (evidence / "expired-evidence").mkdir(parents=True)
    monkeypatch.setattr(retention, "Session", session)
    monkeypatch.setattr(retention, "ROOT", bundles)
    monkeypatch.setattr(retention, "EVIDENCE", evidence)

    report = retention.purge_expired(now)

    assert report["sessions"] == 1
    assert report["resources"] == 2
    assert (bundles / "shared").is_dir()
    assert not (bundles / "private").exists()
    assert not (evidence / "expired-evidence").exists()


def test_stale_staging_is_removed_without_expired_sessions(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(UTC)
    staging = tmp_path / "bundles" / ".staging" / "abandoned"
    staging.mkdir(parents=True)
    old = (now - timedelta(days=2)).timestamp()
    os.utime(staging, (old, old))
    monkeypatch.setattr(retention, "Session", session)
    monkeypatch.setattr(retention, "ROOT", tmp_path / "bundles")
    monkeypatch.setattr(retention, "EVIDENCE", tmp_path / "evidence")

    report = retention.purge_expired(now)

    assert report == {
        "sessions": 0,
        "resources": 0,
        "bundles": 0,
        "evidence": 0,
        "staging": 1,
    }
    assert not staging.exists()


def test_durable_queued_row_is_dispatched_once(monkeypatch):
    row = SimpleNamespace(
        id="job-1",
        kind="neighbourhood",
        status="queued",
        payload={"request": {"longitude": 1}},
    )

    class Database:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def get(self, *_):
            return row

    class RedisConnection:
        def set(self, *_args, **_kwargs):
            return True

        def delete(self, *_):
            return 1

    calls = []

    class Queue:
        def __init__(self, *_args, **_kwargs):
            pass

        def fetch_job(self, *_):
            return None

        def enqueue(self, *args, **kwargs):
            calls.append((args, kwargs))

    monkeypatch.setattr(queueing, "Session", lambda: Database())
    monkeypatch.setattr(queueing.Redis, "from_url", lambda *_args, **_kwargs: RedisConnection())
    monkeypatch.setattr(queueing, "Queue", Queue)

    assert queueing.ensure_enqueued("job-1") is True
    assert calls[0][0][0] == "services.api.jobs.prepare_job"
    assert calls[0][1]["job_id"] == "job-1"
