from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.seed.controller import SeedController
from app.modules.seed.schemas import SeedResponse
from app.modules.seed.service import SeedService

router = APIRouter(prefix="/seed", tags=["seed"])


@router.post("/create-readings", response_model=SeedResponse)
def create_readings(db: Session = Depends(get_db)) -> SeedResponse:
    """
    Resetea cows, collars y readings, y recarga con las 25 vacas
    del life stories (5 por clase: sana, mastitis, celo, febril, digestivo).
    Genera datos desde 2 días atrás hasta 4 días adelante.

    ⚠ Destructivo: borra todos los registros existentes.
    """
    controller = SeedController(SeedService(db))
    return controller.create_readings()