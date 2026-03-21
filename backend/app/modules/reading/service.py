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
        total_stmt = select(func.count(Reading.id)).where(Reading.cow_id == cow_id)
        total = self.db.scalar(total_stmt) or 0

        stmt = (
            select(Reading)
            .where(Reading.cow_id == cow_id)
            .order_by(Reading.timestamp.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        items = list(self.db.scalars(stmt).all())
        return items, total

    def get_recent_by_cow(self, cow_id: int, limit: int) -> list[Reading]:
        stmt = (
            select(Reading)
            .where(Reading.cow_id == cow_id)
            .order_by(Reading.timestamp.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def list_latests(self) -> list[Reading]:
        latest_ranked = select(
            Reading.id.label("reading_id"),
            func.row_number()
            .over(
                partition_by=Reading.cow_id,
                order_by=(Reading.timestamp.desc(), Reading.id.desc()),
            )
            .label("row_num"),
        ).subquery()

        stmt = (
            select(Reading)
            .join(latest_ranked, Reading.id == latest_ranked.c.reading_id)
            .where(latest_ranked.c.row_num == 1)
            .order_by(Reading.cow_id.asc())
        )
        return list(self.db.scalars(stmt).all())
