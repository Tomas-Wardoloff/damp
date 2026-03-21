import logging
import os

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.model import load_model
from app.predictor import build_features, predict_top2
from app.schemas import ClassProbability, PredictRequest, PredictResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="DAMP AI Service", version="2.0.0")

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
    return {"service": "damp-ai", "version": "2.0.0", "status": "ok"}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/predict", response_model=PredictResponse)
def predict(payload: PredictRequest) -> PredictResponse:
    try:
        model = load_model()

        features = build_features(payload.readings, model)

        primary_label, primary_conf, secondary_label, secondary_conf = predict_top2(
            model, features
        )

        return PredictResponse(
            cow_id=str(payload.cow_id),
            primary=ClassProbability(
                label=primary_label,
                confidence=round(primary_conf, 4),
            ),
            secondary=ClassProbability(
                label=secondary_label,
                confidence=round(secondary_conf, 4),
            ),
            alert=primary_label != "sana",
            n_readings_used=len(payload.readings),
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