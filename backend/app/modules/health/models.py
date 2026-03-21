from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.shared.enums import HealthStatus


class HealthAnalysis(Base):
    __tablename__ = "health_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    cow_id: Mapped[int] = mapped_column(ForeignKey("cows.id"), nullable=False, index=True)
    status: Mapped[HealthStatus] = mapped_column(Enum(HealthStatus), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    cow = relationship("Cow", back_populates="health_analyses")
