import numpy as np
import pandas as pd
import pickle
from pathlib import Path
 
 
class MastitisPredictor:
   

    #levantamos el modelo ya entrenado
 
    def __init__(self, model_path: str = "models/mastitis_model.pkl"):
        if not Path(model_path).exists():
            raise FileNotFoundError(
                f"Modelo no encontrado: {model_path}\n"
                "  Ejecutá primero: python train.py"
            )
        with open(model_path, "rb") as f:
            artifact = pickle.load(f)
 
        self.model            = artifact["model"]
        self.scaler           = artifact["scaler"]
        self.le               = artifact["label_encoder"]
        self.feature_names    = artifact["feature_names"]
        self.window_size      = artifact["window_size"]
        self.numeric_features = artifact["numeric_features"]
        self.bool_features    = artifact["bool_features"]
        #self.static_features  = artifact["static_features"]
 
        print(f"✅ Modelo cargado | window={self.window_size} | "
              f"clases={list(self.le.classes_)}")
 
    def _extract_features(self, window: pd.DataFrame) -> pd.DataFrame:
        """Replica exacta del feature engineering de train.py."""
        feats = {}
        n = len(window)
        x = np.arange(n)
 
        for col in self.numeric_features:
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
 
        for col in self.bool_features:
            vals = window[col].values.astype(float)
            feats[f"{col}_rate"]   = np.mean(vals)
            feats[f"{col}_last10"] = np.mean(vals[-10:])
 
        # for col in self.static_features:
        #     feats[col] = window[col].iloc[-1]
 
        if "latitud" in window.columns and "longitud" in window.columns:
            lat_range = window["latitud"].max() - window["latitud"].min()
            lon_range = window["longitud"].max() - window["longitud"].min()
            feats["gps_spread"] = np.sqrt(lat_range**2 + lon_range**2) * 111000
 
        return pd.DataFrame([feats])[self.feature_names]
 
    def predict(self, records) -> dict:

        df = pd.DataFrame(records) if isinstance(records, list) else records.copy()
 
        if len(df) < self.window_size:
            raise ValueError(
                f"Se necesitan al menos {self.window_size} registros. "
                f"Recibidos: {len(df)}"
            )
 
        window   = df.tail(self.window_size).reset_index(drop=True)
        X_feat   = self._extract_features(window)
        X_scaled = self.scaler.transform(X_feat)
 
        proba_arr  = self.model.predict_proba(X_scaled)[0]
        pred_idx   = int(np.argmax(proba_arr))
        label      = self.le.classes_[pred_idx]
        confidence = float(proba_arr[pred_idx])
 
        proba_dict = {
            cls: round(float(p), 4)
            for cls, p in zip(self.le.classes_, proba_arr)
        }
 
        return {
            "label":          label,
            "confidence":     round(confidence, 4),
            "proba":          proba_dict,
            "alert":          label != "sana",
            "n_records_used": len(window),
        }
 
    def predict_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Predice el estado actual de múltiples animales a la vez.
 
        Args:
            df: DataFrame con columna `animal_id` y `timestamp`, ordenado
                cronológicamente.
 
        Returns:
            DataFrame con una fila por animal.
        """
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
                    "proba_sana":        pred["proba"].get("sana", 0),
                    "proba_sub_clinica": pred["proba"].get("sub_clinica", 0),
                    "proba_clinica":     pred["proba"].get("clinica", 0),
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
 
 
# ── Función de alto nivel ─────────────────────────────────────────────────────
 
def predict_animal(records, model_path: str = "mastitis_model.pkl") -> dict:
    """Shortcut stateless para un solo animal."""
    return MastitisPredictor(model_path).predict(records)
 
 
# ── Demo ──────────────────────────────────────────────────────────────────────
 
def _run_demo():
    csv_path = Path("damp_data_test.csv")
    if not csv_path.exists():
        print("❌ damp_data_test.csv no encontrado.")
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
        print(f"    Probas    : sana={result['proba']['sana']:.3f}  "
              f"sub_clínica={result['proba']['subclinica']:.3f}  "
              f"clínica={result['proba']['clinica']:.3f}")
 
    print("\n" + "═"*65)
    print("\n  DEMO BATCH: todos los animales...")
    batch = predictor.predict_batch(df)
    alerts = batch[batch["alert"] == True]
    print(f"  Analizados : {len(batch)}")
    print(f"  Alertas    : {len(alerts)}")
    print("\n  Distribución predicha:")
    for label, cnt in batch["label"].value_counts().items():
        print(f"    {label:12s}: {cnt}")
 
 
if __name__ == "__main__":
    _run_demo()