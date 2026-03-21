import numpy as np
import pandas as pd
import pickle
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers compartidos
# ─────────────────────────────────────────────────────────────────────────────

def _extract_features(window: pd.DataFrame,
                      numeric_features: list,
                      bool_features: list,
                      feature_names: list) -> pd.DataFrame:
    """Feature engineering de train.py (Pipeline sklearn)."""
    feats = {}
    n = len(window)
    x = np.arange(n)

    for col in numeric_features:
        vals = window[col].values.astype(float)
        feats[f"{col}_mean"]      = np.mean(vals)
        feats[f"{col}_std"]       = np.std(vals)
        feats[f"{col}_min"]       = np.min(vals)
        feats[f"{col}_max"]       = np.max(vals)
        feats[f"{col}_range"]     = np.max(vals) - np.min(vals)
        feats[f"{col}_last5"]     = np.mean(vals[-5:])
        feats[f"{col}_last10"]    = np.mean(vals[-10:])
        slope = np.polyfit(x, vals, 1)[0] if np.std(x) > 0 else 0.0
        feats[f"{col}_slope"]     = slope
        feats[f"{col}_crossings"] = int(np.sum(np.diff(np.sign(vals - np.mean(vals))) != 0))

    for col in bool_features:
        vals = window[col].values.astype(float)
        feats[f"{col}_rate"]   = np.mean(vals)
        feats[f"{col}_last10"] = np.mean(vals[-10:])

    if "latitud" in window.columns and "longitud" in window.columns:
        lat_range = window["latitud"].max() - window["latitud"].min()
        lon_range = window["longitud"].max() - window["longitud"].min()
        feats["gps_spread"] = np.sqrt(lat_range**2 + lon_range**2) * 111000

    return pd.DataFrame([feats])[feature_names]


# ─────────────────────────────────────────────────────────────────────────────
#  Backends de inferencia
# ─────────────────────────────────────────────────────────────────────────────

class _SklearnBackend:
    """Inferencia con Pipeline sklearn (train.py)."""

    def __init__(self, artifact: dict):
        self.model            = artifact["model"]
        self.le               = artifact["label_encoder"]
        self.feature_names    = artifact["feature_names"]
        self.window_size      = artifact["window_size"]
        self.numeric_features = artifact["numeric_features"]
        self.bool_features    = artifact["bool_features"]
        print(f"✅ Modelo sklearn (GBC Pipeline) cargado | "
              f"window={self.window_size} | clases={list(self.le.classes_)}")

    def predict(self, window: pd.DataFrame) -> dict:
        X_feat    = _extract_features(window,
                                      self.numeric_features,
                                      self.bool_features,
                                      self.feature_names)
        proba_arr = self.model.predict_proba(X_feat)[0]
        return proba_arr, self.le


class _RNNBackend:
    """Inferencia con red RNN PyTorch (experiment.py)."""

    def __init__(self, artifact: dict):
        import torch
        import torch.nn as nn

        self.le               = artifact["label_encoder"]
        self.scaler           = artifact["scaler"]
        self.window_size      = artifact["window_size"]
        self.numeric_features = artifact["numeric_features"]
        self.bool_features    = artifact["bool_features"]
        self.model_type       = artifact["model_type"]

        n_features = artifact["n_features"]
        n_classes  = artifact["n_classes"]
        hp         = artifact["hparams"]

        # Reconstruir arquitectura sin importar experiment.py
        class _RNN(nn.Module):
            def __init__(self):
                super().__init__()
                rnn_cls  = nn.LSTM if artifact["model_type"] == "lstm" else nn.GRU
                self.rnn = rnn_cls(
                    input_size=n_features,
                    hidden_size=hp["hidden_size"],
                    num_layers=hp["num_layers"],
                    dropout=hp["dropout"] if hp["num_layers"] > 1 else 0.0,
                    batch_first=True,
                )
                self.head = nn.Sequential(
                    nn.Linear(hp["hidden_size"], 64),
                    nn.ReLU(),
                    nn.Dropout(hp["dropout"]),
                    nn.Linear(64, n_classes),
                )

            def forward(self, x):
                out, _ = self.rnn(x)
                return self.head(out[:, -1, :])

        self.model = _RNN()
        self.model.load_state_dict(artifact["model_state"])
        self.model.eval()

        print(f"✅ Modelo {self.model_type.upper()} (PyTorch RNN) cargado | "
              f"window={self.window_size} | clases={list(self.le.classes_)}")

    def predict(self, window: pd.DataFrame) -> tuple:
        import torch

        seq    = window[self.numeric_features + self.bool_features].values.astype(float)
        n_feat = seq.shape[1]
        seq_sc = self.scaler.transform(seq.reshape(-1, n_feat)).reshape(1, self.window_size, n_feat)
        seq_sc = np.nan_to_num(seq_sc, nan=0.0, posinf=0.0, neginf=0.0)

        with torch.no_grad():
            logits    = self.model(torch.tensor(seq_sc, dtype=torch.float32))
            proba_arr = torch.softmax(logits, dim=1).numpy()[0]

        return proba_arr, self.le


# ─────────────────────────────────────────────────────────────────────────────
#  Clase pública
# ─────────────────────────────────────────────────────────────────────────────

class MastitisPredictor:

    # Rutas por defecto (se prueban en orden si no se pasa model_path)
    _DEFAULT_PATHS = [
        "models/mastitis_model.pkl",          # train.py  → sklearn
        "models/experiment_lstm_meta.pkl",    # experiment.py → LSTM
        "models/experiment_gru_meta.pkl",     # experiment.py → GRU
    ]

    def __init__(self, model_path: str = None):
        path = self._resolve_path(model_path)
        with open(path, "rb") as f:
            artifact = pickle.load(f)

        # Detectar tipo por claves del pickle
        if "model" in artifact:
            self._backend = _SklearnBackend(artifact)
        elif "model_state" in artifact:
            self._backend = _RNNBackend(artifact)
        else:
            raise KeyError(
                f"Pickle no reconocido: {path}\n"
                f"  Claves encontradas: {list(artifact.keys())}\n"
                "  Se esperaba 'model' (sklearn) o 'model_state' (PyTorch)."
            )

    # ── API pública ───────────────────────────────────────────────────────────

    def predict(self, records) -> dict:
        df = pd.DataFrame(records) if isinstance(records, list) else records.copy()

        ws = self._backend.window_size
        if len(df) < ws:
            raise ValueError(
                f"Se necesitan al menos {ws} registros. Recibidos: {len(df)}"
            )

        window    = df.tail(ws).reset_index(drop=True)
        proba_arr, le = self._backend.predict(window)

        pred_idx   = int(np.argmax(proba_arr))
        label      = le.classes_[pred_idx]
        confidence = float(proba_arr[pred_idx])
        proba_dict = {cls: round(float(p), 4)
                      for cls, p in zip(le.classes_, proba_arr)}

        return {
            "label":          label,
            "confidence":     round(confidence, 4),
            "proba":          proba_dict,
            "alert":          label != "sana",
            "n_records_used": len(window),
        }

    def predict_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        results = []
        for animal_id, group in df.groupby("animal_id"):
            group_sorted = group.sort_values("timestamp")
            try:
                pred = self.predict(group_sorted)
                results.append({
                    "animal_id":         animal_id,
                    "label":             pred["label"],
                    "confidence":        pred["confidence"],
                    "alert":             pred["alert"],
                    "proba_sana":        pred["proba"].get("sana", 0.0),
                    "proba_sub_clinica": pred["proba"].get("sub_clinica", 0.0),
                    "proba_clinica":     pred["proba"].get("clinica", 0.0),
                    "n_records_used":    pred["n_records_used"],
                })
            except ValueError as e:
                results.append({
                    "animal_id": animal_id,
                    "label":     "sin_datos",
                    "alert":     None,
                    "error":     str(e),
                })
        return pd.DataFrame(results)

    # ── Helpers internos ──────────────────────────────────────────────────────

    @staticmethod
    def _resolve_path(model_path):
        if model_path is not None:
            p = Path(model_path)
            if not p.exists():
                raise FileNotFoundError(f"Modelo no encontrado: {model_path}")
            return p

        for candidate in MastitisPredictor._DEFAULT_PATHS:
            if Path(candidate).exists():
                print(f"  Usando modelo: {candidate}")
                return Path(candidate)

        raise FileNotFoundError(
            "No se encontró ningún modelo. Paths buscados:\n"
            + "\n".join(f"  - {p}" for p in MastitisPredictor._DEFAULT_PATHS)
            + "\nEjecutá primero train.py o experiment.py"
        )


# ─────────────────────────────────────────────────────────────────────────────
#  Shortcut stateless
# ─────────────────────────────────────────────────────────────────────────────

def predict_animal(records, model_path: str = None) -> dict:
    return MastitisPredictor(model_path).predict(records)


# ─────────────────────────────────────────────────────────────────────────────
#  Demo
# ─────────────────────────────────────────────────────────────────────────────

def _run_demo():
    csv_path = Path("data/damp_data_test.csv")
    if not csv_path.exists():
        print(f"❌ {csv_path} no encontrado.")
        return

    predictor = MastitisPredictor()
    df        = pd.read_csv(csv_path, parse_dates=["timestamp"])

    sample_animals = df["animal_id"].unique()[:5]

    print("\n" + "═"*65)
    print("  DEMO: Predicciones sobre animales del dataset sintético")
    print("═"*65)

    for animal_id in sample_animals:
        animal_df  = df[df["animal_id"] == animal_id].sort_values("timestamp")
        real_label = animal_df["label"].iloc[-1]
        result     = predictor.predict(animal_df)
        alert_icon = "🚨" if result["alert"] else "✅"

        print(f"\n  Animal #{animal_id}  |  Real: {real_label:12s}  |  "
              f"Pred: {result['label']:12s}  {alert_icon}")
        print(f"    Confianza : {result['confidence']:.1%}")
        print(f"    Probas    : sana={result['proba'].get('sana', 0):.3f}  "
              f"sub_clínica={result['proba'].get('sub_clinica', 0):.3f}  "
              f"clínica={result['proba'].get('clinica', 0):.3f}")

    print("\n" + "═"*65)
    print("\n  DEMO BATCH: todos los animales...")
    batch  = predictor.predict_batch(df)
    alerts = batch[batch["alert"] == True]

    print(f"  Analizados : {len(batch)}")
    print(f"  Alertas    : {len(alerts)}")
    print("\n  Distribución predicha:")
    for label, cnt in batch["label"].value_counts().items():
        print(f"    {label:12s}: {cnt}")


if __name__ == "__main__":
    _run_demo()