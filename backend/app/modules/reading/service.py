from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.collar.models import Collar
from app.modules.cow.models import Cow
from app.modules.reading.models import Reading
from app.modules.reading.schemas import ReadingCreate


class ReadingService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: ReadingCreate) -> Reading | None:
        collar = self.db.scalar(select(Collar).where(Collar.id == payload.collar_id))
        if collar is None or collar.assigned_cow_id is None:
            return None

        cow = self.db.scalar(select(Cow).where(Cow.id == collar.assigned_cow_id))
        if cow is None:
            return None

        reading = Reading(**payload.model_dump(), cow_id=collar.assigned_cow_id)
        self.db.add(reading)
        self.db.commit()
        self.db.refresh(reading)
        return reading

    def list_by_cow(self, cow_id: int, page: int, size: int) -> tuple[list[Reading], int]:
        now_utc = datetime.utcnow()
        total_stmt = select(func.count(Reading.id)).where(
            Reading.cow_id == cow_id,
            Reading.timestamp <= now_utc,
        )
        total = self.db.scalar(total_stmt) or 0

        stmt = (
            select(Reading)
            .where(
                Reading.cow_id == cow_id,
                Reading.timestamp <= now_utc,
            )
            .order_by(Reading.timestamp.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        items = list(self.db.scalars(stmt).all())
        return items, total

    def get_recent_by_cow(self, cow_id: int, limit: int) -> list[Reading]:
        now_utc = datetime.utcnow()
        stmt = (
            select(Reading)
            .where(
                Reading.cow_id == cow_id,
                Reading.timestamp <= now_utc,
            )
            .order_by(Reading.timestamp.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def list_latests(self) -> list[Reading]:
        now_utc = datetime.utcnow()
        cow_ids_stmt = select(Cow.id).order_by(Cow.id.asc())
        cow_ids = list(self.db.scalars(cow_ids_stmt).all())

        items: list[Reading] = []
        for cow_id in cow_ids:
            latest_stmt = (
                select(Reading)
                .where(
                    Reading.cow_id == cow_id,
                    Reading.timestamp <= now_utc,
                )
                .order_by(Reading.timestamp.desc(), Reading.id.desc())
                .limit(1)
            )
            latest = self.db.scalar(latest_stmt)
            if latest is not None:
                items.append(latest)

        return items
