from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.collar.models import Collar
from app.modules.cow.models import Cow


class CollarService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self) -> Collar:
        collar = Collar(assigned_at=datetime.utcnow())
        self.db.add(collar)
        self.db.commit()
        self.db.refresh(collar)
        return collar

    def get_by_id(self, collar_id: int) -> Collar | None:
        stmt = select(Collar).where(Collar.id == collar_id)
        return self.db.scalar(stmt)

    def assign_to_cow(self, collar_id: int, cow_id: int) -> Collar | None:
        collar = self.get_by_id(collar_id)
        if collar is None:
            return None
        cow = self.db.scalar(select(Cow).where(Cow.id == cow_id))
        if cow is None:
            return None
        collar.assigned_cow_id = cow_id
        collar.assigned_at = datetime.utcnow()
        collar.unassigned_at = None
        self.db.commit()
        self.db.refresh(collar)
        return collar

    def unassign(self, collar_id: int) -> Collar | None:
        collar = self.get_by_id(collar_id)
        if collar is None:
            return None
        collar.assigned_cow_id = None
        collar.unassigned_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(collar)
        return collar
