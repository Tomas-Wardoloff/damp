import sys
import numpy as np
import pandas as pd
import pickle
from pathlib import Path


class MastitisPredictor:
    def __init__(self, model_path: str = "models/nuevas-clases/mastitis_model_v6.pkl"):
        if not Path(model_path).exists():
            raise FileNotFoundError(
                f"Modelo no encontrado: {model_path}\n"
                "  Ejecutá primero: python train.py"
            )
        with open(model_path, "rb") as f:
            artifact = pickle.load(f)

        self.model            = artifact["model"]
        self.le               = artifact["label_encoder"]
        self.feature_names    = artifact["feature_names"]
        self.window_size      = artifact["window_size"]
        self.numeric_features = artifact["numeric_features"]
        self.bool_features    = artifact["bool_features"]

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

        if "latitud" in window.columns and "longitud" in window.columns:
            lat_range = window["latitud"].max() - window["latitud"].min()
            lon_range = window["longitud"].max() - window["longitud"].min()
            feats["gps_spread"] = np.sqrt(lat_range**2 + lon_range**2) * 111000

        # Features temporales — deben coincidir exactamente con train.py
        if "timestamp" in window.columns:
            hours = pd.to_datetime(window["timestamp"]).dt.hour.values
            feats["hour_mean"]        = np.mean(hours)
            feats["night_ratio"]      = np.mean((hours >= 22) | (hours <= 5))
            feats["metro_night_mean"] = np.mean(
                window["metros_recorridos"].values[
                    (hours >= 22) | (hours <= 5)
                ]
            ) if np.any((hours >= 22) | (hours <= 5)) else 0.0

        return pd.DataFrame([feats])[self.feature_names]

    def predict(self, records) -> dict:
        df = pd.DataFrame(records) if isinstance(records, list) else records.copy()

        if len(df) < self.window_size:
            raise ValueError(
                f"Se necesitan al menos {self.window_size} registros. "
                f"Recibidos: {len(df)}"
            )

        window    = df.tail(self.window_size).reset_index(drop=True)
        X_feat    = self._extract_features(window)
        proba_arr = self.model.predict_proba(X_feat)[0]

        pred_idx   = int(np.argmax(proba_arr))
        label      = self.le.classes_[pred_idx]
        confidence = float(proba_arr[pred_idx])

        # Usamos las clases reales del modelo como claves (sin asumir nombres)
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
        """Predice el estado actual de múltiples animales a la vez."""
        results = []
        for animal_id, group in df.groupby("animal_id"):
            group_sorted = group.sort_values("timestamp")
            try:
                pred = self.predict(group_sorted)
                row = {
                    "animal_id":      animal_id,
                    "label":          pred["label"],
                    "confidence":     pred["confidence"],
                    "alert":          pred["alert"],
                    "n_records_used": pred["n_records_used"],
                }
                # Agrega una columna por cada clase que el modelo conozca
                for cls, p in pred["proba"].items():
                    row[f"proba_{cls}"] = p
                results.append(row)
            except ValueError as e:
                results.append({
                    "animal_id": animal_id,
                    "label":     "sin_datos",
                    "alert":     None,
                    "error":     str(e),
                })

        return pd.DataFrame(results)


# ── Helpers de impresión ──────────────────────────────────────────────────────

def _print_result(animal_id, real_label, result: dict):
    alert_icon = "🚨" if result["alert"] else "✅"
    print(f"\n  Animal #{animal_id}  |  Real: {real_label:15s}  |  "
          f"Pred: {result['label']:15s}  {alert_icon}")
    print(f"    Confianza : {result['confidence']:.1%}")
    # Imprime todas las probabilidades usando las claves reales del dict
    proba_str = "  ".join(
        f"{cls}={p:.3f}" for cls, p in result["proba"].items()
    )
    print(f"    Probas    : {proba_str}")


# ── Selector de CSV ───────────────────────────────────────────────────────────

def _listar_csvs(data_dir: str = "data-pruebas/data") -> list[Path]:
    """Devuelve lista ordenada de CSVs en el directorio."""
    p = Path(data_dir)
    if not p.exists():
        print(f"❌ Directorio no encontrado: {data_dir}")
        return []
    csvs = sorted(p.glob("*.csv"))
    return csvs


def _seleccionar_csv(data_dir: str = "data-pruebas/data") -> Path | None:
    """
    Muestra un menú numerado con los CSVs disponibles.
    El usuario ingresa un número para elegir, o 0 para salir.
    Acepta también un número pasado por argumento de línea de comandos.
    """
    csvs = _listar_csvs(data_dir)
    if not csvs:
        return None

    print("\n" + "─" * 55)
    print("  CSVs disponibles:")
    print("─" * 55)
    for i, csv in enumerate(csvs, start=1):
        print(f"  [{i:2d}]  {csv.name}")
    print("─" * 55)

    # Si se pasó un número como argumento de línea de comandos, usarlo directo
    if len(sys.argv) > 1:
        raw = sys.argv[1]
    else:
        raw = input("  Ingresá el número del CSV (0 para salir): ").strip()

    if raw == "0" or raw == "":
        return None

    try:
        idx = int(raw)
        if 1 <= idx <= len(csvs):
            return csvs[idx - 1]
        else:
            print(f"  ❌ Número fuera de rango (1-{len(csvs)})")
            return None
    except ValueError:
        print(f"  ❌ '{raw}' no es un número válido")
        return None


# ── Demo ──────────────────────────────────────────────────────────────────────

def _run_demo():
    csv_path = _seleccionar_csv()
    if csv_path is None:
        print("  Saliendo.")
        return

    print(f"\n  📂 Cargando: {csv_path.name}")

    predictor = MastitisPredictor()
    df        = pd.read_csv(csv_path, parse_dates=["timestamp"])

    sample_animals = df["animal_id"].unique()[:5]

    print("\n" + "═" * 65)
    print("  DEMO: Predicciones sobre animales del dataset sintético")
    print("═" * 65)

    for animal_id in sample_animals:
        animal_df  = df[df["animal_id"] == animal_id].sort_values("timestamp")
        real_label = animal_df["label"].iloc[-1] if "label" in animal_df.columns else "desconocido"
        result     = predictor.predict(animal_df)
        _print_result(animal_id, real_label, result)

    print("\n" + "═" * 65)
    print("\n  DEMO BATCH: todos los animales...")
    batch  = predictor.predict_batch(df)
    alerts = batch[batch["alert"] == True]

    print(f"  Analizados : {len(batch)}")
    print(f"  Alertas    : {len(alerts)}")
    print("\n  Distribución predicha:")
    for label, cnt in batch["label"].value_counts().items():
        print(f"    {label:15s}: {cnt}")


if __name__ == "__main__":
    _run_demo()