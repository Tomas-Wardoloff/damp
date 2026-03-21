"""add dual health prediction fields

Revision ID: 20260321_0005
Revises: 20260321_0004
Create Date: 2026-03-21 01:30:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260321_0005"
down_revision = "20260321_0004"
branch_labels = None
depends_on = None


health_status_enum_column = sa.Enum(
    "SANA",
    "SUBCLINICA",
    "CLINICA",
    "MASTITIS",
    "CELO",
    "FEBRIL",
    "DIGESTIVO",
    name="healthstatus",
    create_type=False,
)


def upgrade() -> None:
    op.add_column("health_analyses", sa.Column("model_cow_id", sa.String(length=120), nullable=True))
    op.add_column("health_analyses", sa.Column("primary_status", health_status_enum_column, nullable=True))
    op.add_column("health_analyses", sa.Column("primary_confidence", sa.Float(), nullable=True))
    op.add_column("health_analyses", sa.Column("secondary_status", health_status_enum_column, nullable=True))
    op.add_column("health_analyses", sa.Column("secondary_confidence", sa.Float(), nullable=True))
    op.add_column("health_analyses", sa.Column("alert", sa.Boolean(), nullable=True))
    op.add_column("health_analyses", sa.Column("n_readings_used", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("health_analyses", "n_readings_used")
    op.drop_column("health_analyses", "alert")
    op.drop_column("health_analyses", "secondary_confidence")
    op.drop_column("health_analyses", "secondary_status")
    op.drop_column("health_analyses", "primary_confidence")
    op.drop_column("health_analyses", "primary_status")
    op.drop_column("health_analyses", "model_cow_id")
