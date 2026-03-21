from pathlib import Path
import warnings
warnings.filterwarnings("ignore")
 
import numpy as np
import pandas as pd
import pickle
 
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import StratifiedGroupKFold, train_test_split
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import (classification_report, confusion_matrix,f1_score, accuracy_score)

CSV_PATH = "damp_data.csv"
MODEL_PATH      = "models/mastitis_model.pkl"
WINDOW_SIZE     = 50
STEP_SIZE       = 10
N_FOLDS         = 5
SEED            = 42

NUMERIC_FEATURES = [
    "temperatura_corporal_prom",
    "frec_cardiaca_prom",
    "rmssd",
    "sdnn",
    "metros_recorridos",
    "velocidad_movimiento_prom",
]
BOOL_FEATURES   = ["hubo_rumia", "hubo_vocalizacion"]
#STATIC_FEATURES = ["edad_animal"]


def extract_window_features(window: pd.DataFrame) -> dict:
    feats = {}
    n = len(window)
    x = np.arange(n)
 
    for col in NUMERIC_FEATURES:
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
 
    for col in BOOL_FEATURES:
        vals = window[col].values.astype(float)
        feats[f"{col}_rate"]   = np.mean(vals)
        feats[f"{col}_last10"] = np.mean(vals[-10:])
 
    # for col in STATIC_FEATURES:
    #     feats[col] = window[col].iloc[-1]
 
    if "latitud" in window.columns and "longitud" in window.columns:
        lat_range = window["latitud"].max() - window["latitud"].min()
        lon_range = window["longitud"].max() - window["longitud"].min()
        feats["gps_spread"] = np.sqrt(lat_range**2 + lon_range**2) * 111000
 
    return feats


def build_windowed_dataset(df: pd.DataFrame):
    all_feats, all_labels, all_groups = [], [], []
 
    for animal_id, group in df.groupby("animal_id"):
        group = group.sort_values("timestamp").reset_index(drop=True)
        n = len(group)
        for start in range(0, n - WINDOW_SIZE + 1, STEP_SIZE):
            window = group.iloc[start : start + WINDOW_SIZE]
            label  = window["label"].iloc[-1]
            all_feats.append(extract_window_features(window))
            all_labels.append(label)
            all_groups.append(animal_id)
 
    X      = pd.DataFrame(all_feats)
    groups = np.array(all_groups)
    le     = LabelEncoder()
    y      = le.fit_transform(all_labels)
 
    return X, y, groups, le

# ── Entrenamiento ─────────────────────────────────────────────────────────────
 
def make_model():
    """Instancia el clasificador con los hiperparámetros del MVP."""
    return GradientBoostingClassifier(
        n_estimators=200,
        learning_rate=0.08,
        max_depth=4,
        min_samples_leaf=20,
        subsample=0.8,
        random_state=SEED,
    )
 
 
def train_model(X: pd.DataFrame, y: np.ndarray, groups: np.ndarray):
    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(X)
 
    cv        = StratifiedGroupKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    oof_preds = np.zeros(len(y), dtype=int)
 
    print(f"\nEntrenando con {N_FOLDS}-fold StratifiedGroupKFold...")
    print(f"Dataset: {len(X):,} ventanas | {X.shape[1]} features\n")
 
    for fold, (train_idx, val_idx) in enumerate(cv.split(X_scaled, y, groups), 1):
        X_tr, X_val = X_scaled[train_idx], X_scaled[val_idx]
        y_tr, y_val = y[train_idx],         y[val_idx]
 
        model = make_model()
        model.fit(X_tr, y_tr)
 
        val_preds          = model.predict(X_val)
        oof_preds[val_idx] = val_preds
        fold_f1            = f1_score(y_val, val_preds, average="macro")
        print(f"  Fold {fold}/{N_FOLDS}  →  F1-macro: {fold_f1:.4f}")
 
    print("\nEntrenando modelo final sobre todo el dataset...")
    final_model = make_model()
    final_model.fit(X_scaled, y)
 
    return final_model, scaler, oof_preds
 
# mas simple para debug del modelo.
def train_model(X, y, groups):
    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Split 80/20 — group-aware para no mezclar animales entre train y test
    animals      = np.unique(groups)
    train_animals, test_animals = train_test_split(
        animals, test_size=0.2, random_state=SEED
    )
    train_idx = np.isin(groups, train_animals)
    test_idx  = np.isin(groups, test_animals)

    X_train, X_test = X_scaled[train_idx], X_scaled[test_idx]
    y_train, y_test = y[train_idx],         y[test_idx]

    print(f"  Train: {train_idx.sum():,} ventanas ({len(train_animals)} animales)")
    print(f"  Test : {test_idx.sum():,} ventanas ({len(test_animals)} animales)\n")

    model = make_model()
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    return model, scaler, y_test, y_pred

# ── Evaluación ────────────────────────────────────────────────────────────────
 
def evaluate(y_true, y_pred, le):
    labels = le.classes_
    acc    = accuracy_score(y_true, y_pred)
    f1     = f1_score(y_true, y_pred, average="macro")
 
    print("\n" + "═"*55)
    print("  RESULTADOS OUT-OF-FOLD (sin data leakage)")
    print("═"*55)
    print(f"  Accuracy   : {acc:.4f}")
    print(f"  F1-macro   : {f1:.4f}")
    print("\n  Reporte por clase:")
    print(classification_report(y_true, y_pred, target_names=labels, digits=4))
 
    cm = confusion_matrix(y_true, y_pred)
    print("  Matriz de confusión (filas=real, cols=predicho):")
    header = "         " + "  ".join(f"{l:>10}" for l in labels)
    print(header)
    for i, row in enumerate(cm):
        print(f"  {labels[i]:>8} " + "  ".join(f"{v:>10}" for v in row))
    print("═"*55)
 
 
def print_feature_importance(model, feature_names, top_n=15):
    imp = pd.Series(model.feature_importances_, index=feature_names)
    imp = imp.sort_values(ascending=False).head(top_n)
    print(f"\n  Top {top_n} features más importantes:")
    for feat, score in imp.items():
        bar = "█" * int(score / imp.max() * 30)
        print(f"    {feat:45s} {bar} {score:.4f}")
 
 
# ── Main ──────────────────────────────────────────────────────────────────────
 
def main():
    print(f"Cargando {CSV_PATH}...")
    df = pd.read_csv(CSV_PATH, parse_dates=["timestamp"])
    print(f"  {len(df):,} filas | {df['animal_id'].nunique()} animales")
    print(f"  Período: {df['timestamp'].min()} → {df['timestamp'].max()}")
 
    print("\nConstruyendo ventanas deslizantes (window=50, step=10)...")
    X, y, groups, le = build_windowed_dataset(df)
    print(f"  → {len(X):,} ventanas | {X.shape[1]} features")
 
    unique, counts = np.unique(y, return_counts=True)
    print("\n  Distribución de ventanas por clase:")
    for cls_idx, cnt in zip(unique, counts):
        print(f"    {le.classes_[cls_idx]:12s}: {cnt:,} ({cnt/len(y)*100:.1f}%)")
 
    # Entrenamos con solo el split de 80/20 no por folds, es mas facil de entender este metodo
    final_model, scaler, y_test, y_pred = train_model(X, y, groups)

    evaluate(y_test, y_pred, le)
    print_feature_importance(final_model, list(X.columns))
 
    artifact = {
        "model":            final_model,
        "scaler":           scaler,
        "label_encoder":    le,
        "feature_names":    list(X.columns),
        "window_size":      WINDOW_SIZE,
        "numeric_features": NUMERIC_FEATURES,
        "bool_features":    BOOL_FEATURES,
      #  "static_features":  STATIC_FEATURES,
    }
    Path(MODEL_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(artifact, f)
 
    print(f"\n✅ Modelo guardado en: {MODEL_PATH}")
    print("   Para inferencia: python predict.py")
 
 
if __name__ == "__main__":
    main()