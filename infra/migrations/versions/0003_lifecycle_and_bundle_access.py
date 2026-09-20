"""Add expiring sessions and indexed bundle ownership."""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("sessions", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE sessions SET expires_at = created_at + INTERVAL '7 days'")
    op.alter_column("sessions", "expires_at", nullable=False)
    op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"])

    op.add_column("resources", sa.Column("bundle_id", sa.String(64), nullable=True))
    op.execute("UPDATE resources SET bundle_id = payload->>'bundle_id' WHERE payload->>'bundle_id' IS NOT NULL")
    op.create_index(
        "ix_resources_bundle_access",
        "resources",
        ["bundle_id", "status", "session_id"],
    )


def downgrade():
    op.drop_index("ix_resources_bundle_access", table_name="resources")
    op.drop_column("resources", "bundle_id")
    op.drop_index("ix_sessions_expires_at", table_name="sessions")
    op.drop_column("sessions", "expires_at")
