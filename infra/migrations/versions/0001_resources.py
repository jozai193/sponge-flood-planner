"""Initial session and immutable resource metadata."""
from alembic import op
import sqlalchemy as sa
revision="0001"
down_revision=None
branch_labels=None
depends_on=None

def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.create_table("sessions",sa.Column("id",sa.String(64),primary_key=True),
        sa.Column("token_hash",sa.String(64),nullable=False,unique=True),
        sa.Column("revision",sa.Integer,nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_table("resources",sa.Column("id",sa.String(64),primary_key=True),
        sa.Column("session_id",sa.String(64),sa.ForeignKey("sessions.id")),
        sa.Column("kind",sa.String(40),nullable=False),sa.Column("status",sa.String(40),nullable=False),
        sa.Column("payload",sa.JSON,nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_resources_session_id","resources",["session_id"])
    op.create_index("ix_resources_kind","resources",["kind"])

def downgrade():
    op.drop_table("resources")
    op.drop_table("sessions")
