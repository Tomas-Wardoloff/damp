import httpx

from app.core.config import settings
from app.shared.enums import HealthStatus


class AIClient:
    async def predict(self, readings: list[dict]) -> HealthStatus:
        url = f"{settings.ai_service_url.rstrip('/')}/predict"
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(url, json={"readings": readings})
            response.raise_for_status()
            payload = response.json()
            return HealthStatus(payload["status"])
