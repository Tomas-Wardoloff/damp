from datetime import datetime

from pydantic import BaseModel, Field

from app.shared.enums import HealthStatus


class HealthAnalysisResponse(BaseModel):
    id: int
    cow_id: int
    status: HealthStatus
    confidence: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class HealthSchedulerConfigResponse(BaseModel):
    enabled: bool
    cycle_minutes: int
    updated_at: datetime

    model_config = {"from_attributes": True}


class HealthSchedulerConfigUpdate(BaseModel):
    enabled: bool
    cycle_minutes: int = Field(ge=1, le=10080)


class HealthSchedulerRuntimeResponse(BaseModel):
    running: bool
    last_execution_at: datetime | None
    current_per_cow_seconds: int | None
