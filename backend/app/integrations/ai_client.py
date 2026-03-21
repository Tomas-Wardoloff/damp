import httpx
from pydantic import BaseModel

from app.core.config import settings
from app.shared.enums import HealthStatus


class AIPredictionResult(BaseModel):
    model_cow_id: str | None = None
    primary_status: HealthStatus | None = None
    primary_confidence: float | None = None
    secondary_status: HealthStatus | None = None
    secondary_confidence: float | None = None
    alert: bool | None = None
    n_readings_used: int | None = None


def _parse_label(raw_label: object) -> HealthStatus | None:
    if raw_label is None:
        return None
    return HealthStatus.from_model_value(str(raw_label))


def _parse_confidence(raw_confidence: object) -> float | None:
    if raw_confidence is None:
        return None
    return float(raw_confidence)


class AIClient:
    async def predict(self, cow_id: int, readings: list[dict]) -> AIPredictionResult:
        url = f"{settings.ai_service_url.rstrip('/')}/predict"
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(url, json={"cow_id": cow_id, "readings": readings})
            response.raise_for_status()
            payload = response.json()

            # Backward compatibility: support previous response format {status, confidence}
            if "status" in payload and "primary" not in payload:
                return AIPredictionResult(
                    model_cow_id=str(payload.get("cow_id")) if payload.get("cow_id") is not None else None,
                    primary_status=_parse_label(payload.get("status")),
                    primary_confidence=_parse_confidence(payload.get("confidence")),
                    alert=bool(payload.get("alert")) if payload.get("alert") is not None else None,
                    n_readings_used=int(payload.get("n_readings_used")) if payload.get("n_readings_used") is not None else None,
                )

            primary = payload.get("primary") or {}
            secondary = payload.get("secondary") or {}
            return AIPredictionResult(
                model_cow_id=str(payload.get("cow_id")) if payload.get("cow_id") is not None else None,
                primary_status=_parse_label(primary.get("label")),
                primary_confidence=_parse_confidence(primary.get("confidence")),
                secondary_status=_parse_label(secondary.get("label")),
                secondary_confidence=_parse_confidence(secondary.get("confidence")),
                alert=bool(payload.get("alert")) if payload.get("alert") is not None else None,
                n_readings_used=int(payload.get("n_readings_used")) if payload.get("n_readings_used") is not None else None,
            )
