"""Store provider attachment IDs separately from provider message IDs."""

from alembic import op
from sqlalchemy import Column, String, inspect

revision = "0002_attachment_provider_id"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = inspect(connection)
    columns = {column["name"] for column in inspector.get_columns("attachments")}
    if "provider_attachment_id" not in columns:
        op.add_column(
            "attachments",
            Column("provider_attachment_id", String(length=255), nullable=True),
        )
    unique_constraints = inspect(connection).get_unique_constraints("attachments")
    constraints = {constraint["name"] for constraint in unique_constraints}
    if "uq_email_provider_attachment" not in constraints:
        op.create_unique_constraint(
            "uq_email_provider_attachment",
            "attachments",
            ["email_id", "provider_attachment_id"],
        )


def downgrade() -> None:
    op.drop_constraint("uq_email_provider_attachment", "attachments", type_="unique")
    op.drop_column("attachments", "provider_attachment_id")
