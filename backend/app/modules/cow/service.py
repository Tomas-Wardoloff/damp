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

    def get_summary(self) -> dict:
        cows = self.list_all()
        if not cows:
            return {"summary": {}, "cows": []}

        now_utc = datetime.utcnow()

        # Latest reading per cow (1 SQL query)
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
            .where(Reading.timestamp <= now_utc)
            .subquery()
        )
        stmt_r = select(Reading).join(
            ranked_readings,
            Reading.id == ranked_readings.c.reading_id,
        ).where(
            ranked_readings.c.row_num == 1,
        )
        latest_readings: dict[int, Reading] = {
            r.cow_id: r for r in self.db.scalars(stmt_r).all()
        }

        # Latest health analysis per cow (1 SQL query)
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
            .where(HealthAnalysis.created_at <= now_utc)
            .subquery()
        )
        stmt_h = select(HealthAnalysis).join(
            ranked_health,
            HealthAnalysis.id == ranked_health.c.health_id,
        ).where(
            ranked_health.c.row_num == 1,
        )
        latest_health: dict[int, HealthAnalysis] = {
            h.cow_id: h for h in self.db.scalars(stmt_h).all()
        }

        summary_counts: Counter = Counter()
        cows_list = []

        for cow in cows:
            reading = latest_readings.get(cow.id)
            health = latest_health.get(cow.id)

            status = "sin datos"
            if health and health.status:
                status = health.status.value.lower()
            summary_counts[status] += 1

            cows_list.append(
                {
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
                }
            )

        return {"summary": dict(summary_counts), "cows": cows_list}
