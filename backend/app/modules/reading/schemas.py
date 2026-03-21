from datetime import datetime

from pydantic import BaseModel

from app.shared.utils import build_pagination


class ReadingPayload(BaseModel):
    timestamp: datetime
    temperatura_corporal_prom: float
    hubo_rumia: bool
    frec_cardiaca_prom: float
    rmssd: float
    sdnn: float
    hubo_vocalizacion: bool
    latitud: float
    longitud: float
    metros_recorridos: float
    velocidad_movimiento_prom: float


class ReadingCreate(ReadingPayload):
    collar_id: int


class ReadingResponse(ReadingPayload):
    id: int
    cow_id: int
    collar_id: int

    model_config = {"from_attributes": True}


class ReadingListResponse(BaseModel):
    items: list[ReadingResponse]
    page: int
    size: int
    total: int
    pages: int

    @classmethod
    def from_items(cls, items: list[ReadingResponse], page: int, size: int, total: int) -> "ReadingListResponse":
        return cls(items=items, **build_pagination(page=page, size=size, total=total))
