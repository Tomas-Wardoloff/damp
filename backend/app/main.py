from fastapi import FastAPI

from app.core.config import settings
from app.core.database import Base, engine
from app.modules.collar.routes import router as collar_router
from app.modules.cow.routes import router as cow_router
from app.modules.health.routes import router as health_router
from app.modules.reading.routes import router as reading_router

app = FastAPI(title=settings.app_name, debug=settings.app_debug)


@app.on_event("startup")
def on_startup() -> None:
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)


@app.get("/")
def healthcheck() -> dict:
    return {
        "message": "Livestock Health API running",
        "environment": settings.app_env,
    }


app.include_router(cow_router)
app.include_router(collar_router)
app.include_router(reading_router)
app.include_router(health_router)
