import logging

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
        readings_stmt = (
            select(Reading)
            .where(Reading.cow_id == cow_id)
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
            status_value = await self.ai_client.predict(cow_id=cow_id, readings=readings_for_model)
        except httpx.HTTPError as exc:
            logger.exception("AI service request failed for cow_id=%s", cow_id)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI service unavailable or returned an invalid response",
            ) from exc

        analysis = HealthAnalysis(cow_id=cow_id, status=status_value)
        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)

        if status_value == HealthStatus.CLINICA:
            logger.critical("CRITICAL ALERT cow_id=%s status=%s", cow_id, status_value)
        elif status_value == HealthStatus.SUBCLINICA:
            logger.warning("WARNING ALERT cow_id=%s status=%s", cow_id, status_value)

        return analysis

    def history(self, cow_id: int) -> list[HealthAnalysis]:
        stmt = (
            select(HealthAnalysis)
            .where(HealthAnalysis.cow_id == cow_id)
            .order_by(HealthAnalysis.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

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
