"""Create the baseline purchase-order schema without replacing existing tables."""

from alembic import op

from app.db import Base

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    # The baseline may represent a pre-existing database, so dropping it is unsafe.
    pass
