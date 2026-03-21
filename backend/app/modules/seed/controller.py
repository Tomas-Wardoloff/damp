from app.modules.seed.service import SeedService
from app.modules.seed.schemas import SeedResponse


class SeedController:
    def __init__(self, service: SeedService) -> None:
        self.service = service

    def create_readings(self) -> SeedResponse:
        result = self.service.create_readings()
        return SeedResponse(**result)