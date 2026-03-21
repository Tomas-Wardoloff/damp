import httpx
from pydantic import BaseModel

from app.core.config import settings
from app.shared.enums import HealthStatus


class AIPredictionResult(BaseModel):
    status: HealthStatus
    confidence: float | None = None


class AIClient:
    async def predict(self, cow_id: int, readings: list[dict]) -> AIPredictionResult:
        url = f"{settings.ai_service_url.rstrip('/')}/predict"
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(url, json={"cow_id": cow_id, "readings": readings})
            response.raise_for_status()
            payload = response.json()

            raw_confidence = payload.get("confidence")
            confidence = float(raw_confidence) if raw_confidence is not None else None
            return AIPredictionResult(
                status=HealthStatus.from_model_value(payload["status"]),
                confidence=confidence,
            )
