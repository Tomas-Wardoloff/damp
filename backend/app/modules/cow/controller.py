from fastapi import HTTPException, status

from app.modules.cow.schemas import CowCreate
from app.modules.cow.service import CowService


class CowController:
    def __init__(self, service: CowService) -> None:
        self.service = service

    def create(self, payload: CowCreate):
        return self.service.create(payload)

    def list_all(self):
        return self.service.list_all()

    def get_by_id(self, cow_id: int):
        cow = self.service.get_by_id(cow_id)
        if cow is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cow not found")
        return cow

    def get_summary(self):
        return self.service.get_summary()
