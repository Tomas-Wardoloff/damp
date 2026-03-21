from datetime import datetime

from pydantic import BaseModel, Field


class CowCreate(BaseModel):
    breed: str = Field(min_length=1, max_length=120)
    registration_date: datetime
    age_months: int = Field(ge=0)


class CowResponse(BaseModel):
    id: int
    breed: str
    registration_date: datetime
    age_months: int

    model_config = {"from_attributes": True}


class CowSummaryItem(BaseModel):
    id: str
    breed: str
    status: str
    temperature: float | str
    heartRate: float | str
    distance: float | str
    latitud: float | str | None = None
    longitud: float | str | None = None
    lastUpdated: str
    healthCreatedAt: str | None = None
    confidence: float | None = None
    primaryStatus: str | None = None
    primaryConfidence: float | None = None
    secondaryStatus: str | None = None
    secondaryConfidence: float | None = None


class CowSummaryResponse(BaseModel):
    summary: dict[str, int]
    cows: list[CowSummaryItem]
