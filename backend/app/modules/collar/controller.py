from fastapi import HTTPException, status

from app.modules.collar.service import CollarService


class CollarController:
    def __init__(self, service: CollarService) -> None:
        self.service = service

    def create(self):
        return self.service.create()

    def assign_to_cow(self, collar_id: int, cow_id: int):
        collar = self.service.assign_to_cow(collar_id, cow_id)
        if collar is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collar or cow not found",
            )
        return collar

    def unassign(self, collar_id: int):
        collar = self.service.unassign(collar_id)
        if collar is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collar not found")
        return collar
