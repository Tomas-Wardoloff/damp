from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.collar.controller import CollarController
from app.modules.collar.schemas import CollarResponse
from app.modules.collar.service import CollarService

router = APIRouter(prefix="/collars", tags=["collars"])


@router.post("", response_model=CollarResponse)
def create_collar(db: Session = Depends(get_db)) -> CollarResponse:
    controller = CollarController(CollarService(db))
    return controller.create()


@router.post("/{collar_id}/assign/{cow_id}", response_model=CollarResponse)
def assign_collar(collar_id: int, cow_id: int, db: Session = Depends(get_db)) -> CollarResponse:
    controller = CollarController(CollarService(db))
    return controller.assign_to_cow(collar_id, cow_id)


@router.post("/{collar_id}/unassign", response_model=CollarResponse)
def unassign_collar(collar_id: int, db: Session = Depends(get_db)) -> CollarResponse:
    controller = CollarController(CollarService(db))
    return controller.unassign(collar_id)
