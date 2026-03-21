"""expand health status enum values

Revision ID: 20260321_0003
Revises: 20260321_0002
Create Date: 2026-03-21 00:30:00
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260321_0003"
down_revision = "20260321_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE healthstatus ADD VALUE IF NOT EXISTS 'MASTITIS';")
    op.execute("ALTER TYPE healthstatus ADD VALUE IF NOT EXISTS 'CELO';")
    op.execute("ALTER TYPE healthstatus ADD VALUE IF NOT EXISTS 'FEBRIL';")
    op.execute("ALTER TYPE healthstatus ADD VALUE IF NOT EXISTS 'DIGESTIVO';")


def downgrade() -> None:
    # PostgreSQL does not support dropping enum values safely in-place.
    # Keeping downgrade as no-op for this migration.
    pass
