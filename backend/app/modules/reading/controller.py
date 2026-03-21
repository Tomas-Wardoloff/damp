from fastapi import HTTPException, status

from app.modules.reading.schemas import ReadingCreate
from app.modules.reading.service import ReadingService


class ReadingController:
    def __init__(self, service: ReadingService) -> None:
        self.service = service

    def create(self, payload: ReadingCreate):
        reading = self.service.create(payload)
        if reading is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cow or collar not found",
            )
        return reading

    def list_by_cow(self, cow_id: int, page: int, size: int):
        return self.service.list_by_cow(cow_id=cow_id, page=page, size=size)

    def list_latests(self):
        return self.service.list_latests()
