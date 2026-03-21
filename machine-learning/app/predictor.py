from typing import Any

import numpy as np
import pandas as pd

from app.schemas import ReadingInput

CLASS_MAPPING = {
    0: "SANA",
    1: "SUBCLINICA",
    2: "CLINICA",
    "sana": "SANA",
    "sub_clinica": "SUBCLINICA",
    "subclinica": "SUBCLINICA",
    "subclínica": "SUBCLINICA",
    "clinica": "CLINICA",
    "clínica": "CLINICA",
}


def _safe_std(values: np.ndarray) -> float:
    return float(np.std(values)) if values.size > 1 else 0.0


def _slope(values: np.ndarray) -> float:
    n = values.size
    if n < 2:
        return 0.0
    x = np.arange(n, dtype=float)
    return float(np.polyfit(x, values.astype(float), 1)[0])


def _crossings(values: np.ndarray) -> float:
    if values.size < 2:
        return 0.0
    centered = values - float(np.mean(values))
    return float(np.sum(np.diff(np.sign(centered)) != 0))


def _to_dataframe(readings: list[ReadingInput]) -> pd.DataFrame:
    rows = [
        {
            "temperatura_corporal_prom": float(r.temperatura_corporal_prom),
            "frec_cardiaca_prom": float(r.frec_cardiaca_prom),
            "rmssd": float(r.rmssd),
            "sdnn": float(r.sdnn),
            "metros_recorridos": float(r.metros_recorridos),
            "velocidad_movimiento_prom": float(r.velocidad_movimiento_prom),
            "hubo_rumia": int(r.hubo_rumia),
            "hubo_vocalizacion": int(r.hubo_vocalizacion),
            "latitud": np.nan,
            "longitud": np.nan,
        }
        for r in readings
    ]
    return pd.DataFrame(rows)


def _extract_window_features(
    window: pd.DataFrame,
    numeric_features: list[str],
    bool_features: list[str],
) -> dict[str, float]:
    feats: dict[str, float] = {}

    for col in numeric_features:
        vals = pd.to_numeric(window[col], errors="coerce").fillna(0.0).to_numpy(dtype=float)
        feats[f"{col}_mean"] = float(np.mean(vals))
        feats[f"{col}_std"] = _safe_std(vals)
        feats[f"{col}_min"] = float(np.min(vals))
        feats[f"{col}_max"] = float(np.max(vals))
        feats[f"{col}_range"] = float(np.max(vals) - np.min(vals))
        feats[f"{col}_last5"] = float(np.mean(vals[-5:]))
        feats[f"{col}_last10"] = float(np.mean(vals[-10:]))
        feats[f"{col}_slope"] = _slope(vals)
        feats[f"{col}_crossings"] = _crossings(vals)

    for col in bool_features:
        vals = window[col].astype(int).to_numpy(dtype=float)
        feats[f"{col}_rate"] = float(np.mean(vals))
        feats[f"{col}_last10"] = float(np.mean(vals[-10:]))

    if "latitud" in window.columns and "longitud" in window.columns:
        lat = pd.to_numeric(window["latitud"], errors="coerce")
        lon = pd.to_numeric(window["longitud"], errors="coerce")
        if lat.notna().any() and lon.notna().any():
            lat_range = float(lat.max() - lat.min())
            lon_range = float(lon.max() - lon.min())
            feats["gps_spread"] = float(np.sqrt(lat_range**2 + lon_range**2) * 111000)

    if "gps_spread" not in feats:
        feats["gps_spread"] = 0.0

    return feats


def _build_rnn_sequence(readings: list[ReadingInput], model: Any) -> np.ndarray:
    df = _to_dataframe(readings)

    window_size = int(getattr(model, "_damp_window_size", 300) or 300)
    if len(df) < window_size:
        raise ValueError(
            f"Se necesitan al menos {window_size} lecturas para este modelo. Recibidas: {len(df)}"
        )

    numeric_features = list(
        getattr(model, "_damp_numeric_features", None)
        or [
            "temperatura_corporal_prom",
            "frec_cardiaca_prom",
            "rmssd",
            "sdnn",
            "metros_recorridos",
            "velocidad_movimiento_prom",
        ]
    )
    bool_features = list(
        getattr(model, "_damp_bool_features", None)
        or ["hubo_rumia", "hubo_vocalizacion"]
    )
    feature_cols = numeric_features + bool_features

    window = df.tail(window_size).reset_index(drop=True).copy()
    for col in bool_features:
        window[col] = window[col].astype(float)

    x = window[feature_cols].astype(float).to_numpy(dtype=float)

    scaler = getattr(model, "_damp_scaler", None)
    if scaler is not None:
        x = scaler.transform(x)

    x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
    return x.reshape(1, window_size, len(feature_cols)).astype(np.float32)


def build_features(readings: list[ReadingInput], model: Any) -> np.ndarray:
    if getattr(model, "_damp_model_type", None):
        return _build_rnn_sequence(readings, model)

    window = _to_dataframe(readings)

    numeric_features = list(
        getattr(model, "_damp_numeric_features", None)
        or [
            "temperatura_corporal_prom",
            "frec_cardiaca_prom",
            "rmssd",
            "sdnn",
            "metros_recorridos",
            "velocidad_movimiento_prom",
        ]
    )
    bool_features = list(
        getattr(model, "_damp_bool_features", None)
        or ["hubo_rumia", "hubo_vocalizacion"]
    )

    feats = _extract_window_features(window, numeric_features, bool_features)

    feature_names = getattr(model, "_damp_feature_names", None)
    if feature_names:
        vector = [float(feats.get(name, 0.0)) for name in feature_names]
    else:
        vector = [float(feats[name]) for name in sorted(feats)]

    return np.asarray(vector, dtype=float).reshape(1, -1)


def _normalize_status(raw: Any) -> str:
    if isinstance(raw, (np.integer, int)):
        return CLASS_MAPPING.get(int(raw), "SANA")
    return CLASS_MAPPING.get(str(raw).strip().lower(), "SANA")


def predict_status(model: Any, features: np.ndarray) -> tuple[str, float | None]:
    prediction_raw = model.predict(features)[0]
    label_encoder = getattr(model, "_damp_label_encoder", None)

    if label_encoder is not None and isinstance(prediction_raw, (np.integer, int)):
        decoded = label_encoder.inverse_transform([int(prediction_raw)])[0]
        status = _normalize_status(decoded)
    else:
        status = _normalize_status(prediction_raw)

    confidence: float | None = None
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(features)
        confidence = float(np.max(probabilities[0]))

    return status, confidence
