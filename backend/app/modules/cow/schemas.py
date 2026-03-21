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
