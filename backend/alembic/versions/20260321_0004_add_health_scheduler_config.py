"""add health scheduler config table

Revision ID: 20260321_0004
Revises: 20260321_0003
Create Date: 2026-03-21 01:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260321_0004"
down_revision = "20260321_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "health_scheduler_configs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("cycle_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("health_scheduler_configs")
