from app.modules.health.service import HealthService


class HealthController:
    def __init__(self, service: HealthService) -> None:
        self.service = service

    async def analyze(self, cow_id: int, limit: int | None = None):
        return await self.service.analyze(cow_id, limit=limit)

    async def status(self, cow_id: int):
        return await self.service.status(cow_id)

    def history(self, cow_id: int):
        return self.service.history(cow_id)
