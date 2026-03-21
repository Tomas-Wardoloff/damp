from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.cow.models import Cow
from app.modules.cow.schemas import CowCreate


class CowService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: CowCreate) -> Cow:
        cow = Cow(**payload.model_dump())
        self.db.add(cow)
        self.db.commit()
        self.db.refresh(cow)
        return cow

    def list_all(self) -> list[Cow]:
        stmt = select(Cow).order_by(Cow.id.asc())
        return list(self.db.scalars(stmt).all())

    def get_by_id(self, cow_id: int) -> Cow | None:
        stmt = select(Cow).where(Cow.id == cow_id)
        return self.db.scalar(stmt)
