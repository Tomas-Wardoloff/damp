"""initial schema

Revision ID: 20260320_0001
Revises:
Create Date: 2026-03-20 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260320_0001"
down_revision = None
branch_labels = None
depends_on = None


health_status_enum = postgresql.ENUM(
    "SANA",
    "SUBCLINICA",
    "CLINICA",
    name="healthstatus",
)

health_status_enum_column = postgresql.ENUM(
    "SANA",
    "SUBCLINICA",
    "CLINICA",
    name="healthstatus",
    create_type=False,
)


def upgrade() -> None:
    op.create_table(
        "cows",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("breed", sa.String(length=120), nullable=False),
        sa.Column("registration_date", sa.DateTime(), nullable=False),
        sa.Column("age_months", sa.Integer(), nullable=False),
    )
    op.create_index("ix_cows_id", "cows", ["id"], unique=False)

    op.create_table(
        "collars",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("assigned_cow_id", sa.Integer(), sa.ForeignKey("cows.id"), nullable=True),
        sa.Column("assigned_at", sa.DateTime(), nullable=False),
        sa.Column("unassigned_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_collars_id", "collars", ["id"], unique=False)

    op.create_table(
        "readings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("cow_id", sa.Integer(), sa.ForeignKey("cows.id"), nullable=False),
        sa.Column("collar_id", sa.Integer(), sa.ForeignKey("collars.id"), nullable=False),
        sa.Column("temperatura_corporal_prom", sa.Float(), nullable=False),
        sa.Column("hubo_rumia", sa.Boolean(), nullable=False),
        sa.Column("frec_cardiaca_prom", sa.Float(), nullable=False),
        sa.Column("rmssd", sa.Float(), nullable=False),
        sa.Column("sdnn", sa.Float(), nullable=False),
        sa.Column("hubo_vocalizacion", sa.Boolean(), nullable=False),
        sa.Column("latitud", sa.Float(), nullable=False),
        sa.Column("longitud", sa.Float(), nullable=False),
        sa.Column("metros_recorridos", sa.Float(), nullable=False),
        sa.Column("velocidad_movimiento_prom", sa.Float(), nullable=False),
    )
    op.create_index("ix_readings_id", "readings", ["id"], unique=False)
    op.create_index("ix_readings_cow_id", "readings", ["cow_id"], unique=False)
    op.create_index("ix_readings_collar_id", "readings", ["collar_id"], unique=False)

    health_status_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "health_analyses",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("cow_id", sa.Integer(), sa.ForeignKey("cows.id"), nullable=False),
        sa.Column("status", health_status_enum_column, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_health_analyses_id", "health_analyses", ["id"], unique=False)
    op.create_index("ix_health_analyses_cow_id", "health_analyses", ["cow_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_health_analyses_cow_id", table_name="health_analyses")
    op.drop_index("ix_health_analyses_id", table_name="health_analyses")
    op.drop_table("health_analyses")
    health_status_enum.drop(op.get_bind(), checkfirst=True)

    op.drop_index("ix_readings_collar_id", table_name="readings")
    op.drop_index("ix_readings_cow_id", table_name="readings")
    op.drop_index("ix_readings_id", table_name="readings")
    op.drop_table("readings")

    op.drop_index("ix_collars_id", table_name="collars")
    op.drop_table("collars")

    op.drop_index("ix_cows_id", table_name="cows")
    op.drop_table("cows")
