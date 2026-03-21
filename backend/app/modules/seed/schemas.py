from pydantic import BaseModel


class SeedResponse(BaseModel):
    cows_created: int
    collars_created: int
    readings_created: int
    analyses_created: int
    message: str