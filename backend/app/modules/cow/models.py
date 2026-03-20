from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Cow(Base):
    __tablename__ = "cows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    breed: Mapped[str] = mapped_column(String(120), nullable=False)
    registration_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    age_months: Mapped[int] = mapped_column(Integer, nullable=False)

    readings = relationship("Reading", back_populates="cow", cascade="all, delete-orphan")
    health_analyses = relationship("HealthAnalysis", back_populates="cow", cascade="all, delete-orphan")
    collars = relationship("Collar", back_populates="assigned_cow")
