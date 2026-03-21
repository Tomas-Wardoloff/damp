from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.reading.controller import ReadingController
from app.modules.reading.schemas import ReadingCreate, ReadingListResponse, ReadingResponse
from app.modules.reading.service import ReadingService

router = APIRouter(tags=["readings"])


@router.post("/readings", response_model=ReadingResponse)
def create_reading(payload: ReadingCreate, db: Session = Depends(get_db)) -> ReadingResponse:
    controller = ReadingController(ReadingService(db))
    return controller.create(payload)


@router.get("/readings/latests", response_model=list[ReadingResponse])
def list_latest_readings(db: Session = Depends(get_db)) -> list[ReadingResponse]:
    controller = ReadingController(ReadingService(db))
    return controller.list_latests()


@router.get("/cows/{cow_id}/readings", response_model=ReadingListResponse)
def list_cow_readings(
    cow_id: int,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
) -> ReadingListResponse:
    controller = ReadingController(ReadingService(db))
    items, total = controller.list_by_cow(cow_id=cow_id, page=page, size=size)
    response_items = [ReadingResponse.model_validate(item) for item in items]
    return ReadingListResponse.from_items(response_items, page=page, size=size, total=total)

