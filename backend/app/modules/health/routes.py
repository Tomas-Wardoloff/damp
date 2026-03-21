from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.integrations.ai_client import AIClient
from app.modules.health.controller import HealthController
from app.modules.health.models import HealthSchedulerConfig
from app.modules.health.schemas import (
    HealthAnalysisResponse,
    HealthSchedulerConfigResponse,
    HealthSchedulerConfigUpdate,
    HealthSchedulerRuntimeResponse,
)
from app.modules.health.service import HealthService

router = APIRouter(prefix="/health", tags=["health"])


def _ensure_scheduler_table(db: Session) -> None:
    bind = db.get_bind()
    HealthSchedulerConfig.__table__.create(bind=bind, checkfirst=True)


@router.post("/analyze/{cow_id}", response_model=HealthAnalysisResponse)
async def analyze_cow_health(
    cow_id: int,
    limit: int = Query(default=settings.health_window_size, ge=1, le=500),
    db: Session = Depends(get_db),
) -> HealthAnalysisResponse:
    controller = HealthController(HealthService(db=db, ai_client=AIClient()))
    return await controller.analyze(cow_id, limit=limit)


@router.get("/status/{cow_id}", response_model=HealthAnalysisResponse | None)
async def get_latest_health_status(
    cow_id: int,
    db: Session = Depends(get_db),
) -> HealthAnalysisResponse | None:
    controller = HealthController(HealthService(db=db, ai_client=AIClient()))
    return await controller.status(cow_id)


@router.get("/history/{cow_id}", response_model=list[HealthAnalysisResponse])
def get_health_history(cow_id: int, db: Session = Depends(get_db)) -> list[HealthAnalysisResponse]:
    controller = HealthController(HealthService(db=db, ai_client=AIClient()))
    return controller.history(cow_id)


@router.get("/scheduler/config", response_model=HealthSchedulerConfigResponse)
def get_scheduler_config(db: Session = Depends(get_db)) -> HealthSchedulerConfigResponse:
    _ensure_scheduler_table(db)
    config = db.scalar(select(HealthSchedulerConfig).order_by(HealthSchedulerConfig.id.asc()).limit(1))
    if config is None:
        config = HealthSchedulerConfig(
            enabled=settings.health_scheduler_enabled,
            cycle_minutes=settings.health_scheduler_cycle_minutes,
            updated_at=datetime.utcnow(),
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    return HealthSchedulerConfigResponse.model_validate(config)


@router.put("/scheduler/config", response_model=HealthSchedulerConfigResponse)
def update_scheduler_config(
    payload: HealthSchedulerConfigUpdate,
    request: Request,
    db: Session = Depends(get_db),
) -> HealthSchedulerConfigResponse:
    _ensure_scheduler_table(db)
    config = db.scalar(select(HealthSchedulerConfig).order_by(HealthSchedulerConfig.id.asc()).limit(1))
    if config is None:
        config = HealthSchedulerConfig(
            enabled=payload.enabled,
            cycle_minutes=max(1, payload.cycle_minutes),
            updated_at=datetime.utcnow(),
        )
        db.add(config)
    else:
        config.enabled = payload.enabled
        config.cycle_minutes = max(1, payload.cycle_minutes)
        config.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(config)

    scheduler = request.app.state.health_scheduler
    scheduler.reset_timing()

    return HealthSchedulerConfigResponse.model_validate(config)


@router.get("/scheduler/runtime", response_model=HealthSchedulerRuntimeResponse)
def get_scheduler_runtime(request: Request) -> HealthSchedulerRuntimeResponse:
    scheduler = request.app.state.health_scheduler
    return HealthSchedulerRuntimeResponse(
        running=scheduler.running,
        last_execution_at=scheduler.last_execution_at,
        current_per_cow_seconds=scheduler.current_per_cow_seconds,
        eligible_cows_count=scheduler.eligible_cows_count,
    )
