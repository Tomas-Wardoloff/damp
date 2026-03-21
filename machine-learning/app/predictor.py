"""
DAMP AI Service - Predictor
Adaptado para 5 clases: sana | mastitis | celo | febril | digestivo
Features idénticas al train.py incluyendo temporales (hour_mean, night_ratio, metro_night_mean)
"""

from typing import Any, Optional
import numpy as np
import pandas as pd

from app.schemas import ReadingInput

# Labels que el modelo conoce — deben coincidir con le.classes_ del train
VALID_LABELS = {"sana", "mastitis", "celo", "febril", "digestivo"}

# Labels que generan alerta (todo menos sana)
ALERT_LABELS = VALID_LABELS - {"sana"}


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
    """Convierte los readings a DataFrame con todos los campos que necesita el extractor."""
    rows = []
    for r in readings:
        rows.append({
            "timestamp":                  r.timestamp,
            "temperatura_corporal_prom":  float(r.temperatura_corporal_prom) if r.temperatura_corporal_prom is not None else np.nan,
            "frec_cardiaca_prom":         float(r.frec_cardiaca_prom),
            "rmssd":                      float(r.rmssd),
            "sdnn":                       float(r.sdnn),
            "metros_recorridos":          float(r.metros_recorridos),
            "velocidad_movimiento_prom":  float(r.velocidad_movimiento_prom),
            "hubo_rumia":                 int(r.hubo_rumia),
            "hubo_vocalizacion":          int(r.hubo_vocalizacion),
            "latitud":                    float(r.latitud) if r.latitud is not None else np.nan,
            "longitud":                   float(r.longitud) if r.longitud is not None else np.nan,
        })
    return pd.DataFrame(rows)


def _extract_window_features(
    window: pd.DataFrame,
    numeric_features: list[str],
    bool_features: list[str],
) -> dict[str, float]:
    """
    Replica exacta del extract_window_features de train.py.
    Incluye los features temporales nocturnos.
    """
    feats: dict[str, float] = {}

    # Features numéricas base
    for col in numeric_features:
        vals = pd.to_numeric(window[col], errors="coerce").fillna(0.0).to_numpy(dtype=float)
        feats[f"{col}_mean"]      = float(np.mean(vals))
        feats[f"{col}_std"]       = _safe_std(vals)
        feats[f"{col}_min"]       = float(np.min(vals))
        feats[f"{col}_max"]       = float(np.max(vals))
        feats[f"{col}_range"]     = float(np.max(vals) - np.min(vals))
        feats[f"{col}_last5"]     = float(np.mean(vals[-5:]))
        feats[f"{col}_last10"]    = float(np.mean(vals[-10:]))
        feats[f"{col}_slope"]     = _slope(vals)
        feats[f"{col}_crossings"] = _crossings(vals)

    # Features booleanas
    for col in bool_features:
        vals = window[col].astype(int).to_numpy(dtype=float)
        feats[f"{col}_rate"]   = float(np.mean(vals))
        feats[f"{col}_last10"] = float(np.mean(vals[-10:]))

    # GPS spread
    if "latitud" in window.columns and "longitud" in window.columns:
        lat = pd.to_numeric(window["latitud"], errors="coerce")
        lon = pd.to_numeric(window["longitud"], errors="coerce")
        if lat.notna().any() and lon.notna().any():
            lat_range = float(lat.max() - lat.min())
            lon_range = float(lon.max() - lon.min())
            feats["gps_spread"] = float(np.sqrt(lat_range**2 + lon_range**2) * 111000)
        else:
            feats["gps_spread"] = 0.0
    else:
        feats["gps_spread"] = 0.0

    # Features temporales nocturnas — idénticas al train.py
    if "timestamp" in window.columns:
        try:
            hours = pd.to_datetime(window["timestamp"]).dt.hour.values
            feats["hour_mean"]        = float(np.mean(hours))
            feats["night_ratio"]      = float(np.mean((hours >= 22) | (hours <= 5)))
            night_mask = (hours >= 22) | (hours <= 5)
            if np.any(night_mask):
                metros_vals = pd.to_numeric(window["metros_recorridos"], errors="coerce").fillna(0.0).to_numpy(dtype=float)
                feats["metro_night_mean"] = float(np.mean(metros_vals[night_mask]))
            else:
                feats["metro_night_mean"] = 0.0
        except Exception:
            feats["hour_mean"]        = 12.0
            feats["night_ratio"]      = 0.0
            feats["metro_night_mean"] = 0.0
    else:
        feats["hour_mean"]        = 12.0
        feats["night_ratio"]      = 0.0
        feats["metro_night_mean"] = 0.0

    return feats


def build_features(readings: list[ReadingInput], model: Any) -> np.ndarray:
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
        # Usar el orden exacto del entrenamiento, rellenar con 0 si falta alguno
        vector = [float(feats.get(name, 0.0)) for name in feature_names]
    else:
        vector = [float(feats[name]) for name in sorted(feats)]

    return np.asarray(vector, dtype=float).reshape(1, -1)


def predict_top2(
    model: Any,
    features: np.ndarray,
) -> tuple[str, float, str, float]:
    """
    Devuelve las dos clases más probables con sus confidences.
    Returns: (primary_label, primary_conf, secondary_label, secondary_conf)
    """
    label_encoder = getattr(model, "_damp_label_encoder", None)

    if not hasattr(model, "predict_proba"):
        # Fallback si el modelo no tiene probabilidades
        raw = model.predict(features)[0]
        if label_encoder is not None and isinstance(raw, (np.integer, int)):
            primary = str(label_encoder.inverse_transform([int(raw)])[0])
        else:
            primary = str(raw).strip().lower()
        return primary, 1.0, "sana", 0.0

    probas = model.predict_proba(features)[0]

    # Obtener los labels en el mismo orden que predict_proba
    if label_encoder is not None:
        classes = list(label_encoder.classes_)
    else:
        classes = [str(i) for i in range(len(probas))]

    # Ordenar por probabilidad descendente
    sorted_idx = np.argsort(probas)[::-1]

    primary_label   = str(classes[sorted_idx[0]]).strip().lower()
    primary_conf    = float(probas[sorted_idx[0]])
    secondary_label = str(classes[sorted_idx[1]]).strip().lower() if len(classes) > 1 else "sana"
    secondary_conf  = float(probas[sorted_idx[1]]) if len(probas) > 1 else 0.0

    return primary_label, primary_conf, secondary_label, secondary_conf