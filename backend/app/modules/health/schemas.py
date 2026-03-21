from datetime import datetime

from pydantic import BaseModel

from app.shared.enums import HealthStatus


class HealthAnalysisResponse(BaseModel):
    id: int
    cow_id: int
    status: HealthStatus
    created_at: datetime

    model_config = {"from_attributes": True}
