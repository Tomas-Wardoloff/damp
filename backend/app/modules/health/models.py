from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.shared.enums import HealthStatus


class HealthAnalysis(Base):
    __tablename__ = "health_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    cow_id: Mapped[int] = mapped_column(ForeignKey("cows.id"), nullable=False, index=True)
    model_cow_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    primary_status: Mapped[HealthStatus | None] = mapped_column(Enum(HealthStatus), nullable=True)
    primary_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    secondary_status: Mapped[HealthStatus | None] = mapped_column(Enum(HealthStatus), nullable=True)
    secondary_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    alert: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    n_readings_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[HealthStatus] = mapped_column(Enum(HealthStatus), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    cow = relationship("Cow", back_populates="health_analyses")


class HealthSchedulerConfig(Base):
    __tablename__ = "health_scheduler_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    cycle_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
