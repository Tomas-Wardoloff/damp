"""add confidence to health analyses

Revision ID: 20260321_0002
Revises: 20260320_0001
Create Date: 2026-03-21 00:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260321_0002"
down_revision = "20260320_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("health_analyses", sa.Column("confidence", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("health_analyses", "confidence")
