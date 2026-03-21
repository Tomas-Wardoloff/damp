from pydantic import BaseModel, Field, field_validator
from typing import Optional


class ReadingInput(BaseModel):
    timestamp: str                          # necesario para features nocturnas
    temperatura_corporal_prom: Optional[float] = None   # puede ser None (falla sensor)
    hubo_rumia: int = Field(ge=0, le=1)
    frec_cardiaca_prom: float
    rmssd: float
    sdnn: float
    hubo_vocalizacion: int = Field(ge=0, le=1)
    metros_recorridos: float
    velocidad_movimiento_prom: float
    latitud: Optional[float] = None
    longitud: Optional[float] = None


class ClassProbability(BaseModel):
    label: str
    confidence: float           # 0.0 - 1.0


class PredictRequest(BaseModel):
    cow_id: str                 # puede ser "COW_001" o int, str es más flexible
    readings: list[ReadingInput] = Field(min_length=1, max_length=300)

    @field_validator("readings")
    @classmethod
    def validate_readings_not_empty(cls, value: list[ReadingInput]) -> list[ReadingInput]:
        if not value:
            raise ValueError("readings must not be empty")
        return value


class PredictResponse(BaseModel):
    cow_id: str
    primary: ClassProbability           # clase más probable
    secondary: ClassProbability         # segunda más probable
    alert: bool                         # True si primary != sana
    n_readings_used: int                # cuántos registros se usaron