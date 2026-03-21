from datetime import datetime

from pydantic import BaseModel, Field

from app.shared.enums import HealthStatus


class HealthAnalysisResponse(BaseModel):
    id: int
    cow_id: int
    model_cow_id: str | None = None
    primary_status: HealthStatus | None = None
    primary_confidence: float | None = None
    secondary_status: HealthStatus | None = None
    secondary_confidence: float | None = None
    alert: bool | None = None
    n_readings_used: int | None = None
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
    eligible_cows_count: int
