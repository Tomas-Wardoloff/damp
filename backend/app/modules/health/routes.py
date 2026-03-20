from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.integrations.ai_client import AIClient
from app.modules.health.controller import HealthController
from app.modules.health.schemas import HealthAnalysisResponse
from app.modules.health.service import HealthService

router = APIRouter(prefix="/health", tags=["health"])


@router.post("/analyze/{cow_id}", response_model=HealthAnalysisResponse)
async def analyze_cow_health(cow_id: int, db: Session = Depends(get_db)) -> HealthAnalysisResponse:
    controller = HealthController(HealthService(db=db, ai_client=AIClient()))
    return await controller.analyze(cow_id)


@router.get("/status/{cow_id}", response_model=HealthAnalysisResponse)
async def get_latest_health_status(cow_id: int, db: Session = Depends(get_db)) -> HealthAnalysisResponse:
    controller = HealthController(HealthService(db=db, ai_client=AIClient()))
    return await controller.status(cow_id)


@router.get("/history/{cow_id}", response_model=list[HealthAnalysisResponse])
def get_health_history(cow_id: int, db: Session = Depends(get_db)) -> list[HealthAnalysisResponse]:
    controller = HealthController(HealthService(db=db, ai_client=AIClient()))
    return controller.history(cow_id)
