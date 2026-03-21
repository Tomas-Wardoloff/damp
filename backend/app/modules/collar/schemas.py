from datetime import datetime

from pydantic import BaseModel


class CollarCreate(BaseModel):
    pass


class CollarResponse(BaseModel):
    id: int
    assigned_cow_id: int | None
    assigned_at: datetime
    unassigned_at: datetime | None

    model_config = {"from_attributes": True}
