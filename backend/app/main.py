from fastapi import FastAPI

from app.core.config import APP_DEBUG, APP_ENV, APP_NAME

app = FastAPI(title=APP_NAME)


@app.get("/")
def healthcheck() -> dict:
    return {
        "message": "FastAPI project is running",
        "environment": APP_ENV,
        "debug": APP_DEBUG,
    }
