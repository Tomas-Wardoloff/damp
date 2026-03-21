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


def _parse_bool(raw_flag: object) -> bool | None:
    if raw_flag is None:
        return None
    if isinstance(raw_flag, bool):
        return raw_flag
    if isinstance(raw_flag, (int, float)):
        return raw_flag != 0
    if isinstance(raw_flag, str):
        normalized = raw_flag.strip().lower()
        if normalized in {"true", "1", "yes", "y"}:
            return True
        if normalized in {"false", "0", "no", "n"}:
            return False
    raise ValueError(f"Invalid boolean value: {raw_flag!r}")


def _parse_int(raw_value: object) -> int | None:
    if raw_value is None:
        return None
    return int(raw_value)


class AIClient:
    async def predict(self, cow_id: int, readings: list[dict]) -> AIPredictionResult:
        url = f"{settings.ai_service_url.rstrip('/')}/predict"
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(url, json={"cow_id": cow_id, "readings": readings})
            response.raise_for_status()
            payload = response.json()

            if not isinstance(payload, dict):
                raise TypeError("AI response must be a JSON object")

            primary = payload.get("primary")
            secondary = payload.get("secondary")
            if not isinstance(primary, dict) or not isinstance(secondary, dict):
                raise ValueError("AI response must include 'primary' and 'secondary' objects")

            if "label" not in primary or "confidence" not in primary:
                raise ValueError("AI response 'primary' must include 'label' and 'confidence'")
            if "label" not in secondary or "confidence" not in secondary:
                raise ValueError("AI response 'secondary' must include 'label' and 'confidence'")

            return AIPredictionResult(
                model_cow_id=str(payload.get("cow_id")) if payload.get("cow_id") is not None else None,
                primary_status=_parse_label(primary.get("label")),
                primary_confidence=_parse_confidence(primary.get("confidence")),
                secondary_status=_parse_label(secondary.get("label")),
                secondary_confidence=_parse_confidence(secondary.get("confidence")),
                alert=_parse_bool(payload.get("alert")),
                n_readings_used=_parse_int(payload.get("n_readings_used")),
            )
