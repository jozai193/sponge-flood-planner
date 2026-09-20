"""Register the immutable public Spring Garden sample."""
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import insert

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

SAMPLE_ID = "2c607f51e1a064fc76ee6f5585cbc343358d0e9a39ead1a2806643e21cae37ba"


def upgrade():
    resources = sa.table(
        "resources",
        sa.column("id", sa.String),
        sa.column("session_id", sa.String),
        sa.column("kind", sa.String),
        sa.column("status", sa.String),
        sa.column("payload", sa.JSON),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    now = datetime.now(UTC)
    statement = insert(resources).values({
        "id": SAMPLE_ID,
        "session_id": None,
        "kind": "sample",
        "status": "completed",
        "payload": {"bundle_id": SAMPLE_ID, "label": "Spring Garden, Philadelphia"},
        "created_at": now,
        "updated_at": now,
    }).on_conflict_do_nothing(index_elements=["id"])
    op.get_bind().execute(statement)


def downgrade():
    op.execute(sa.text("DELETE FROM resources WHERE id = :sample_id").bindparams(sample_id=SAMPLE_ID))
