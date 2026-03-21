import logging
import os
import pickle
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _resolve_model_path() -> Path:
    model_path_env = os.getenv("MODEL_PATH")
    if model_path_env:
        return Path(model_path_env).expanduser().resolve()

    base_dir = Path(__file__).resolve().parents[1]
    candidates = [
        base_dir / "models/nuevas-clases/mastitis_model_v7.pkl"
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    # Default expected location if none exists yet.
    return candidates[0]


def _extract_predictor(loaded_obj: Any) -> Any:
    metadata: dict[str, Any] = {}

    if isinstance(loaded_obj, dict):
        metadata = loaded_obj
        for key in ("model", "estimator", "clf", "classifier"):
            candidate = loaded_obj.get(key)
            if candidate is not None:
                loaded_obj = candidate
                break

    if not hasattr(loaded_obj, "predict"):
        raise TypeError("Loaded model object does not implement predict()")

    # Attach optional metadata so predictor can replicate training features.
    setattr(loaded_obj, "_damp_feature_names", metadata.get("feature_names"))
    setattr(loaded_obj, "_damp_numeric_features", metadata.get("numeric_features"))
    setattr(loaded_obj, "_damp_bool_features", metadata.get("bool_features"))
    setattr(loaded_obj, "_damp_window_size", metadata.get("window_size"))
    setattr(loaded_obj, "_damp_label_encoder", metadata.get("label_encoder"))

    return loaded_obj


@lru_cache(maxsize=1)
def load_model() -> Any:
    model_path = _resolve_model_path()

    if not model_path.exists():
        raise FileNotFoundError(
            "Model file not found. Checked MODEL_PATH and default paths: "
            f"{Path(__file__).resolve().parents[1] / 'model.pkl'} and "
            f"{Path(__file__).resolve().parents[1] / 'models' / 'model.pkl'}"
        )

    logger.info("Loading model from %s", model_path)
    with model_path.open("rb") as model_file:
        loaded_obj = pickle.load(model_file)

    model = _extract_predictor(loaded_obj)

    logger.info("Model loaded successfully")
    return model
