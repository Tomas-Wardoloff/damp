from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Collar(Base):
    __tablename__ = "collars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    assigned_cow_id: Mapped[int | None] = mapped_column(ForeignKey("cows.id"), nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    unassigned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    assigned_cow = relationship("Cow", back_populates="collars")
    readings = relationship("Reading", back_populates="collar")
