from collections import Counter

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

        # Latest reading per cow (1 SQL query)
        subq_r = (
            select(Reading.cow_id, func.max(Reading.timestamp).label("max_ts"))
            .group_by(Reading.cow_id)
            .subquery()
        )
        stmt_r = select(Reading).join(
            subq_r,
            (Reading.cow_id == subq_r.c.cow_id) & (Reading.timestamp == subq_r.c.max_ts),
        )
        latest_readings: dict[int, Reading] = {
            r.cow_id: r for r in self.db.scalars(stmt_r).all()
        }

        # Latest health analysis per cow (1 SQL query)
        subq_h = (
            select(HealthAnalysis.cow_id, func.max(HealthAnalysis.created_at).label("max_ts"))
            .group_by(HealthAnalysis.cow_id)
            .subquery()
        )
        stmt_h = select(HealthAnalysis).join(
            subq_h,
            (HealthAnalysis.cow_id == subq_h.c.cow_id)
            & (HealthAnalysis.created_at == subq_h.c.max_ts),
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
                    "lastUpdated": reading.timestamp.isoformat() if reading else "N/A",
                }
            )

        return {"summary": dict(summary_counts), "cows": cows_list}
