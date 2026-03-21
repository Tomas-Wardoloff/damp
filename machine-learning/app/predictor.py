from typing import Any

import numpy as np

from app.schemas import ReadingInput

CLASS_MAPPING = {
    0: "SANA",
    1: "SUBCLINICA",
    2: "CLINICA",
}


def build_features(readings: list[ReadingInput]) -> np.ndarray:
    temperature = np.array([r.temperatura_corporal_prom for r in readings], dtype=float)
    heart_rate = np.array([r.frec_cardiaca_prom for r in readings], dtype=float)
    rmssd = np.array([r.rmssd for r in readings], dtype=float)
    sdnn = np.array([r.sdnn for r in readings], dtype=float)
    distance = np.array([r.metros_recorridos for r in readings], dtype=float)
    speed = np.array([r.velocidad_movimiento_prom for r in readings], dtype=float)
    rumia = np.array([r.hubo_rumia for r in readings], dtype=float)
    vocalization = np.array([r.hubo_vocalizacion for r in readings], dtype=float)

    features = np.array(
        [
            float(np.mean(temperature)),
            float(np.mean(heart_rate)),
            float(np.mean(rmssd)),
            float(np.mean(sdnn)),
            float(np.sum(distance)),
            float(np.mean(speed)),
            float(np.mean(rumia)),
            float(np.mean(vocalization)),
        ],
        dtype=float,
    )

    return features.reshape(1, -1)


def predict_status(model: Any, features: np.ndarray) -> tuple[str, float | None]:
    prediction_raw = model.predict(features)[0]
    prediction_value = int(prediction_raw)
    status = CLASS_MAPPING.get(prediction_value, "SANA")

    confidence: float | None = None
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(features)
        confidence = float(np.max(probabilities[0]))

    return status, confidence
