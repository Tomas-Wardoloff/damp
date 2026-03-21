import logging
from datetime import datetime, timedelta
import re

from fastapi import HTTPException, status
import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations.ai_client import AIClient
from app.modules.cow.models import Cow
from app.modules.health.models import HealthAnalysis
from app.modules.reading.models import Reading
from app.shared.enums import HealthStatus

logger = logging.getLogger(__name__)


class HealthService:
    def __init__(self, db: Session, ai_client: AIClient) -> None:
        self.db = db
        self.ai_client = ai_client

    async def analyze(self, cow_id: int, limit: int | None = None) -> HealthAnalysis:
        cow = self.db.scalar(select(Cow).where(Cow.id == cow_id))
        if cow is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cow not found")

        window = limit or settings.health_window_size
        now_utc = datetime.utcnow()
        readings_stmt = (
            select(Reading)
            .where(
                Reading.cow_id == cow_id,
                Reading.timestamp <= now_utc,
            )
            .order_by(Reading.timestamp.desc())
            .limit(window)
        )
        readings = list(self.db.scalars(readings_stmt).all())
        if len(readings) < window:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Not enough readings to analyze. Required={window}, found={len(readings)}",
            )

        # ML features rely on temporal order, so send from oldest to newest.
        readings_for_model = [self._serialize_reading(r) for r in reversed(readings)]

        try:
            prediction = await self.ai_client.predict(cow_id=cow_id, readings=readings_for_model)
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            logger.exception("AI service request failed for cow_id=%s", cow_id)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI service unavailable or returned an invalid response",
            ) from exc

        ranked_candidates: list[tuple[HealthStatus, float | None]] = []
        if prediction.primary_status is not None:
            ranked_candidates.append((prediction.primary_status, prediction.primary_confidence))
        if prediction.secondary_status is not None:
            ranked_candidates.append((prediction.secondary_status, prediction.secondary_confidence))

        if not ranked_candidates:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI service returned prediction without valid labels",
            )

        effective_status, effective_confidence = max(
            ranked_candidates,
            key=lambda item: item[1] if item[1] is not None else -1.0,
        )

        analysis = HealthAnalysis(
            cow_id=cow_id,
            model_cow_id=prediction.model_cow_id,
            primary_status=prediction.primary_status,
            primary_confidence=prediction.primary_confidence,
            secondary_status=prediction.secondary_status,
            secondary_confidence=prediction.secondary_confidence,
            alert=prediction.alert,
            n_readings_used=prediction.n_readings_used,
            status=effective_status,
            confidence=effective_confidence,
        )
        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)

        if effective_status in {HealthStatus.CLINICA, HealthStatus.MASTITIS}:
            logger.critical("CRITICAL ALERT cow_id=%s status=%s", cow_id, effective_status)
        elif effective_status in {HealthStatus.SUBCLINICA, HealthStatus.FEBRIL, HealthStatus.DIGESTIVO}:
            logger.warning("WARNING ALERT cow_id=%s status=%s", cow_id, effective_status)
        elif effective_status == HealthStatus.CELO:
            logger.info("EVENT cow_id=%s status=%s", cow_id, effective_status)

        return analysis

    async def status(self, cow_id: int) -> HealthAnalysis | None:
        cow = self.db.scalar(select(Cow).where(Cow.id == cow_id))
        if cow is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cow not found")

        now_utc = datetime.utcnow()
        latest_stmt = (
            select(HealthAnalysis)
            .where(
                HealthAnalysis.cow_id == cow_id,
                HealthAnalysis.created_at <= now_utc,
            )
            .order_by(HealthAnalysis.created_at.desc())
            .limit(1)
        )
        return self.db.scalar(latest_stmt)

    def history(self, cow_id: int) -> list[HealthAnalysis]:
        now_utc = datetime.utcnow()
        stmt = (
            select(HealthAnalysis)
            .where(
                HealthAnalysis.cow_id == cow_id,
                HealthAnalysis.created_at <= now_utc,
            )
            .order_by(HealthAnalysis.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    @staticmethod
    def _parse_cow_code(cow_code: str | None) -> int | None:
        if cow_code is None:
            return None

        trimmed = cow_code.strip()
        if not trimmed:
            return None

        match = re.search(r"(\d+)", trimmed)
        if not match:
            return -1

        try:
            return int(match.group(1))
        except ValueError:
            return -1

    def clinical_history(
        self,
        days: int,
        page: int,
        size: int,
        cow_code: str | None = None,
    ) -> tuple[datetime, datetime, list[dict], int, int]:
        to_date = datetime.utcnow()
        from_date = to_date - timedelta(days=days)

        parsed_cow_id = self._parse_cow_code(cow_code)
        if parsed_cow_id == -1:
            return from_date, to_date, [], 0, 0

        where_conditions = [
            HealthAnalysis.created_at >= from_date,
            HealthAnalysis.created_at <= to_date,
        ]
        if parsed_cow_id is not None:
            where_conditions.append(HealthAnalysis.cow_id == parsed_cow_id)

        stmt = select(HealthAnalysis).where(*where_conditions).order_by(
            HealthAnalysis.cow_id.asc(),
            HealthAnalysis.created_at.asc(),
            HealthAnalysis.id.asc(),
        )
        analyses = list(self.db.scalars(stmt).all())

        grouped: dict[int, list[HealthAnalysis]] = {}
        for analysis in analyses:
            grouped.setdefault(int(analysis.cow_id), []).append(analysis)

        cows: list[dict] = []
        for cow_id in sorted(grouped.keys()):
            points = grouped[cow_id]
            transitions = 0
            for i in range(1, len(points)):
                if points[i].status != points[i - 1].status:
                    transitions += 1

            latest = points[-1]
            cows.append(
                {
                    "cow_id": cow_id,
                    "total_points": len(points),
                    "transitions": transitions,
                    "stable": transitions == 0,
                    "latest_status": latest.status,
                    "points": [
                        {
                            "created_at": p.created_at,
                            "status": p.status,
                            "confidence": p.confidence,
                            "primary_status": p.primary_status,
                            "primary_confidence": p.primary_confidence,
                            "secondary_status": p.secondary_status,
                            "secondary_confidence": p.secondary_confidence,
                        }
                        for p in points
                    ],
                }
            )

        total_cows = len(cows)
        total_pages = (total_cows + size - 1) // size if total_cows > 0 else 0
        start = (page - 1) * size
        end = start + size
        paginated_cows = cows[start:end]

        return from_date, to_date, paginated_cows, total_cows, total_pages

    @staticmethod
    def _serialize_reading(reading: Reading) -> dict:
        return {
            "id": reading.id,
            "timestamp": reading.timestamp.isoformat(),
            "cow_id": reading.cow_id,
            "collar_id": reading.collar_id,
            "temperatura_corporal_prom": reading.temperatura_corporal_prom,
            "hubo_rumia": reading.hubo_rumia,
            "frec_cardiaca_prom": reading.frec_cardiaca_prom,
            "rmssd": reading.rmssd,
            "sdnn": reading.sdnn,
            "hubo_vocalizacion": reading.hubo_vocalizacion,
            "latitud": reading.latitud,
            "longitud": reading.longitud,
            "metros_recorridos": reading.metros_recorridos,
            "velocidad_movimiento_prom": reading.velocidad_movimiento_prom,
        }
