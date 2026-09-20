from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from services.api.settings import settings


def now():
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class UserSession(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    revision: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class Resource(Base):
    __tablename__ = "resources"
    __table_args__ = (
        Index("ix_resources_bundle_access", "bundle_id", "status", "session_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str | None] = mapped_column(ForeignKey("sessions.id"), nullable=True, index=True)
    bundle_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(40), default="queued")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 10} if settings.database_url.startswith("postgresql") else {},
)
Session = sessionmaker(engine, expire_on_commit=False)


def update_resource(resource_id, status, **fields):
    with Session.begin() as db:
        row = db.get(Resource, resource_id)
        if row is None:
            raise ValueError("Unknown job")
        row.status = status
        if "bundle_id" in fields:
            row.bundle_id = fields["bundle_id"]
        row.payload = {**row.payload, **fields}
