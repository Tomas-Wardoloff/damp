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
        base_dir / "model.pkl",
        base_dir / "models" / "model.pkl",
        base_dir / "models" / "mastitis_model.pkl",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    # Default expected location if none exists yet.
    return candidates[0]


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
        model = pickle.load(model_file)

    logger.info("Model loaded successfully")
    return model
