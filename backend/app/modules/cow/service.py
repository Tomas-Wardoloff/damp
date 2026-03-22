from collections import Counter
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.cow.models import Cow
from app.modules.cow.schemas import CowCreate
from app.modules.health.models import HealthAnalysis
from app.modules.reading.models import Reading


class CowService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: CowCreate) -> Cow:
        cow = Cow(**payload.model_dump())
        self.db.add(cow)
        self.db.commit()
        self.db.refresh(cow)
        return cow

    def list_all(self) -> list[Cow]:
        stmt = select(Cow).order_by(Cow.id.asc())
        return list(self.db.scalars(stmt).all())

    def get_by_id(self, cow_id: int) -> Cow | None:
        stmt = select(Cow).where(Cow.id == cow_id)
        return self.db.scalar(stmt)

    def _latest_readings_by_cow(
        self,
        now_utc: datetime,
        cow_ids: list[int] | None = None,
    ) -> dict[int, Reading]:
        where_conditions = [Reading.timestamp <= now_utc]
        if cow_ids is not None:
            if len(cow_ids) == 0:
                return {}
            where_conditions.append(Reading.cow_id.in_(cow_ids))

        ranked_readings = (
            select(
                Reading.id.label("reading_id"),
                Reading.cow_id.label("cow_id"),
                func.row_number()
                .over(
                    partition_by=Reading.cow_id,
                    order_by=(Reading.timestamp.desc(), Reading.id.desc()),
                )
                .label("row_num"),
            )
            .where(*where_conditions)
            .subquery()
        )

        stmt = (
            select(Reading)
            .join(ranked_readings, Reading.id == ranked_readings.c.reading_id)
            .where(ranked_readings.c.row_num == 1)
        )
        return {r.cow_id: r for r in self.db.scalars(stmt).all()}

    def _latest_health_by_cow(
        self,
        now_utc: datetime,
        cow_ids: list[int] | None = None,
    ) -> dict[int, HealthAnalysis]:
        where_conditions = [HealthAnalysis.created_at <= now_utc]
        if cow_ids is not None:
            if len(cow_ids) == 0:
                return {}
            where_conditions.append(HealthAnalysis.cow_id.in_(cow_ids))

        ranked_health = (
            select(
                HealthAnalysis.id.label("health_id"),
                HealthAnalysis.cow_id.label("cow_id"),
                func.row_number()
                .over(
                    partition_by=HealthAnalysis.cow_id,
                    order_by=(HealthAnalysis.created_at.desc(), HealthAnalysis.id.desc()),
                )
                .label("row_num"),
            )
            .where(*where_conditions)
            .subquery()
        )

        stmt = (
            select(HealthAnalysis)
            .join(ranked_health, HealthAnalysis.id == ranked_health.c.health_id)
            .where(ranked_health.c.row_num == 1)
        )
        return {h.cow_id: h for h in self.db.scalars(stmt).all()}

    @staticmethod
    def _build_summary_item(cow: Cow, reading: Reading | None, health: HealthAnalysis | None) -> dict:
        status = "sin datos"
        if health and health.status:
            status = health.status.value.lower()

        return {
            "id": str(cow.id),
            "breed": cow.breed or "Mestiza",
            "status": status,
            "temperature": reading.temperatura_corporal_prom if reading else "--",
            "heartRate": round(reading.frec_cardiaca_prom)
            if reading and reading.frec_cardiaca_prom
            else "--",
            "distance": round(reading.metros_recorridos)
            if reading and reading.metros_recorridos
            else "--",
            "latitud": reading.latitud if reading else None,
            "longitud": reading.longitud if reading else None,
            "lastUpdated": reading.timestamp.isoformat() if reading else "N/A",
            "healthCreatedAt": health.created_at.isoformat() if health else None,
            "confidence": health.confidence if health else None,
            "primaryStatus": health.primary_status.value if health and health.primary_status else None,
            "primaryConfidence": health.primary_confidence if health else None,
            "secondaryStatus": health.secondary_status.value if health and health.secondary_status else None,
            "secondaryConfidence": health.secondary_confidence if health else None,
        }

    def _build_summary_counts(self, total_cows: int, latest_health: dict[int, HealthAnalysis]) -> dict[str, int]:
        summary_counts: Counter = Counter()
        for health in latest_health.values():
            if health.status:
                summary_counts[health.status.value.lower()] += 1

        known = sum(summary_counts.values())
        summary_counts["sin datos"] += max(total_cows - known, 0)
        return dict(summary_counts)

    def get_summary(self) -> dict:
        cows = self.list_all()
        if not cows:
            return {"summary": {}, "cows": []}

        now_utc = datetime.utcnow()
        cow_ids = [cow.id for cow in cows]
        latest_readings = self._latest_readings_by_cow(now_utc=now_utc, cow_ids=cow_ids)
        latest_health = self._latest_health_by_cow(now_utc=now_utc, cow_ids=cow_ids)

        cows_list = [
            self._build_summary_item(
                cow=cow,
                reading=latest_readings.get(cow.id),
                health=latest_health.get(cow.id),
            )
            for cow in cows
        ]

        return {
            "summary": self._build_summary_counts(total_cows=len(cows), latest_health=latest_health),
            "cows": cows_list,
        }

    def get_summary_paged(self, page: int, size: int) -> dict:
        now_utc = datetime.utcnow()
        total = self.db.scalar(select(func.count(Cow.id))) or 0
        total_pages = (total + size - 1) // size if total > 0 else 0

        cows_stmt = (
            select(Cow)
            .order_by(Cow.id.asc())
            .offset((page - 1) * size)
            .limit(size)
        )
        page_cows = list(self.db.scalars(cows_stmt).all())
        page_cow_ids = [cow.id for cow in page_cows]

        latest_readings = self._latest_readings_by_cow(now_utc=now_utc, cow_ids=page_cow_ids)
        latest_health_page = self._latest_health_by_cow(now_utc=now_utc, cow_ids=page_cow_ids)
        latest_health_all = self._latest_health_by_cow(now_utc=now_utc, cow_ids=None)

        page_items = [
            self._build_summary_item(
                cow=cow,
                reading=latest_readings.get(cow.id),
                health=latest_health_page.get(cow.id),
            )
            for cow in page_cows
        ]

        return {
            "summary": self._build_summary_counts(total_cows=total, latest_health=latest_health_all),
            "cows": page_items,
            "page": page,
            "size": size,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1 and total_pages > 0,
        }
