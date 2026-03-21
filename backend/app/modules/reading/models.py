from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Reading(Base):
    __tablename__ = "readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    cow_id: Mapped[int] = mapped_column(ForeignKey("cows.id"), nullable=False, index=True)
    collar_id: Mapped[int] = mapped_column(ForeignKey("collars.id"), nullable=False, index=True)

    temperatura_corporal_prom: Mapped[float] = mapped_column(Float, nullable=False)
    hubo_rumia: Mapped[bool] = mapped_column(Boolean, nullable=False)
    frec_cardiaca_prom: Mapped[float] = mapped_column(Float, nullable=False)
    rmssd: Mapped[float] = mapped_column(Float, nullable=False)
    sdnn: Mapped[float] = mapped_column(Float, nullable=False)
    hubo_vocalizacion: Mapped[bool] = mapped_column(Boolean, nullable=False)

    latitud: Mapped[float] = mapped_column(Float, nullable=False)
    longitud: Mapped[float] = mapped_column(Float, nullable=False)
    metros_recorridos: Mapped[float] = mapped_column(Float, nullable=False)
    velocidad_movimiento_prom: Mapped[float] = mapped_column(Float, nullable=False)

    cow = relationship("Cow", back_populates="readings")
    collar = relationship("Collar", back_populates="readings")
