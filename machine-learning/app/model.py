import logging
import os
import pickle
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


def _is_rnn_metadata(metadata: dict[str, Any]) -> bool:
    required = {"scaler", "label_encoder", "model_type", "hparams", "n_features", "n_classes"}
    return required.issubset(set(metadata.keys()))


def _build_rnn_wrapper(metadata: dict[str, Any], meta_path: Path) -> Any:
    try:
        import torch
        import torch.nn as nn
    except Exception as exc:
        raise RuntimeError(
            "RNN metadata detected but PyTorch is not available. "
            "Add 'torch' to requirements and redeploy."
        ) from exc

    model_type = str(metadata["model_type"]).lower()
    if model_type not in {"lstm", "gru"}:
        raise ValueError(f"Unsupported model_type '{model_type}' in metadata")

    hparams = metadata["hparams"]
    n_features = int(metadata["n_features"])
    n_classes = int(metadata["n_classes"])

    class MastitisRNN(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            rnn_cls = nn.LSTM if model_type == "lstm" else nn.GRU
            self.rnn = rnn_cls(
                input_size=n_features,
                hidden_size=int(hparams["hidden_size"]),
                num_layers=int(hparams["num_layers"]),
                dropout=float(hparams["dropout"]) if int(hparams["num_layers"]) > 1 else 0.0,
                batch_first=True,
            )
            self.head = nn.Sequential(
                nn.Linear(int(hparams["hidden_size"]), 64),
                nn.ReLU(),
                nn.Dropout(float(hparams["dropout"])),
                nn.Linear(64, n_classes),
            )

        def forward(self, x: Any) -> Any:
            out, _ = self.rnn(x)
            return self.head(out[:, -1, :])

    model = MastitisRNN()

    stem = meta_path.stem
    if stem.endswith("_meta"):
        weights_name = f"{stem[:-5]}.pt"
    else:
        weights_name = f"{stem}.pt"
    weights_path = meta_path.with_name(weights_name)

    if not weights_path.exists():
        raise FileNotFoundError(
            f"RNN weights file not found for metadata: expected '{weights_path.name}' near '{meta_path.name}'"
        )

    state_dict = torch.load(weights_path, map_location="cpu")
    model.load_state_dict(state_dict)
    model.eval()

    class RNNEstimator:
        def __init__(self, rnn_model: Any, meta: dict[str, Any]) -> None:
            self._model = rnn_model
            self._label_encoder = meta.get("label_encoder")
            self._scaler = meta.get("scaler")
            self._model_family = "rnn"
            self._model_type = model_type
            self._window_size = int(meta.get("window_size", 300))
            self._numeric_features = list(meta.get("numeric_features", []))
            self._bool_features = list(meta.get("bool_features", []))

        def predict(self, x: Any) -> np.ndarray:
            import torch

            arr = np.asarray(x, dtype=np.float32)
            with torch.no_grad():
                logits = self._model(torch.tensor(arr, dtype=torch.float32))
                pred = torch.argmax(logits, dim=1).cpu().numpy()
            return pred

        def predict_proba(self, x: Any) -> np.ndarray:
            import torch

            arr = np.asarray(x, dtype=np.float32)
            with torch.no_grad():
                logits = self._model(torch.tensor(arr, dtype=torch.float32))
                proba = torch.softmax(logits, dim=1).cpu().numpy()
            return proba

    return RNNEstimator(model, metadata)


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


def _extract_predictor(loaded_obj: Any) -> Any:
    metadata: dict[str, Any] = {}

    if isinstance(loaded_obj, dict):
        metadata = loaded_obj
        for key in ("model", "estimator", "clf", "classifier"):
            candidate = loaded_obj.get(key)
            if candidate is not None:
                loaded_obj = candidate
                break

    if isinstance(loaded_obj, dict) and _is_rnn_metadata(metadata):
        loaded_obj = _build_rnn_wrapper(metadata, _resolve_model_path())

    if not hasattr(loaded_obj, "predict"):
        raise TypeError("Loaded model object does not implement predict()")

    # Attach optional metadata so predictor can replicate training features.
    setattr(loaded_obj, "_damp_feature_names", metadata.get("feature_names"))
    setattr(loaded_obj, "_damp_numeric_features", metadata.get("numeric_features"))
    setattr(loaded_obj, "_damp_bool_features", metadata.get("bool_features"))
    setattr(loaded_obj, "_damp_window_size", metadata.get("window_size"))
    setattr(loaded_obj, "_damp_label_encoder", metadata.get("label_encoder"))
    setattr(loaded_obj, "_damp_scaler", metadata.get("scaler"))
    setattr(loaded_obj, "_damp_model_type", metadata.get("model_type"))

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
