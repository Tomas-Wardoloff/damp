import logging
import os

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.model import load_model
from app.predictor import build_features, predict_status
from app.schemas import PredictRequest, PredictResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="DAMP AI Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://damp-backend.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    load_model()


@app.get("/")
def root() -> dict:
    return {"service": "damp-ai", "status": "ok"}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/predict", response_model=PredictResponse)
def predict(payload: PredictRequest) -> PredictResponse:
    try:
        model = load_model()
        features = build_features(payload.readings, model)
        status, confidence = predict_status(model, features)

        return PredictResponse(
            cow_id=payload.cow_id,
            status=status,
            confidence=confidence,
        )
    except ValueError as exc:
        logger.exception("Validation or prediction error")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected prediction error")
        raise HTTPException(status_code=500, detail="Prediction failed") from exc


if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
