from pydantic import BaseModel, Field, field_validator


class ReadingInput(BaseModel):
    temperatura_corporal_prom: float
    hubo_rumia: int = Field(ge=0, le=1)
    frec_cardiaca_prom: float
    rmssd: float
    sdnn: float
    hubo_vocalizacion: int = Field(ge=0, le=1)
    metros_recorridos: float
    velocidad_movimiento_prom: float


class PredictRequest(BaseModel):
    cow_id: int
    readings: list[ReadingInput] = Field(min_length=1, max_length=300)

    @field_validator("readings")
    @classmethod
    def validate_readings_not_empty(cls, value: list[ReadingInput]) -> list[ReadingInput]:
        if not value:
            raise ValueError("readings must not be empty")
        return value


class PredictResponse(BaseModel):
    cow_id: int
    status: str
    confidence: float | None = None
