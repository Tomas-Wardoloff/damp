import logging
import pickle
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).resolve().parents[1] / "model.pkl"


@lru_cache(maxsize=1)
def load_model() -> Any:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model file not found at {MODEL_PATH}")

    logger.info("Loading model from %s", MODEL_PATH)
    with MODEL_PATH.open("rb") as model_file:
        model = pickle.load(model_file)

    logger.info("Model loaded successfully")
    return model
