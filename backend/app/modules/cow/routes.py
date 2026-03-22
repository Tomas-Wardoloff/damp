from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.cow.controller import CowController
from app.modules.cow.schemas import CowCreate, CowResponse, CowSummaryPageResponse, CowSummaryResponse
from app.modules.cow.service import CowService

router = APIRouter(prefix="/cows", tags=["cows"])


@router.post("", response_model=CowResponse)
def create_cow(payload: CowCreate, db: Session = Depends(get_db)) -> CowResponse:
    controller = CowController(CowService(db))
    return controller.create(payload)


@router.get("", response_model=list[CowResponse])
def list_cows(db: Session = Depends(get_db)) -> list[CowResponse]:
    controller = CowController(CowService(db))
    return controller.list_all()


@router.get("/summary", response_model=CowSummaryResponse)
def get_cows_summary(db: Session = Depends(get_db)) -> CowSummaryResponse:
    controller = CowController(CowService(db))
    return controller.get_summary()


@router.get("/summary/paged", response_model=CowSummaryPageResponse)
def get_cows_summary_paged(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_db),
) -> CowSummaryPageResponse:
    controller = CowController(CowService(db))
    return controller.get_summary_paged(page=page, size=size)


@router.get("/{cow_id}", response_model=CowResponse)
def get_cow(cow_id: int, db: Session = Depends(get_db)) -> CowResponse:
    controller = CowController(CowService(db))
    return controller.get_by_id(cow_id)
