from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

from matplotlib import gridspec, pyplot as plt
import numpy as np
import pandas as pd
import pickle

from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import (classification_report, confusion_matrix, f1_score, accuracy_score)
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

CSV_PATH    = "data/damp_data_temporal.csv"
MODEL_PATH  = "models/mastitis_model.pkl"
WINDOW_SIZE = 900
STEP_SIZE   = 30
SEED        = 42

NUMERIC_FEATURES = [
    "temperatura_corporal_prom",
    "frec_cardiaca_prom",
    "rmssd",
    "sdnn",
    "metros_recorridos",
    "velocidad_movimiento_prom",
]
BOOL_FEATURES = ["hubo_rumia", "hubo_vocalizacion"]


LABEL_COLORS = {
    "sana":        "#2ecc71",
    "mastitis":    "#e74c3c",
    "celo":        "#9b59b6",
    "febril":      "#e67e22",
    "digestivo":   "#1abc9c",
}


#Generacion de features para entrenar al modelo
def extract_window_features(window: pd.DataFrame) -> dict:
    feats = {}
    n = len(window)
    x = np.arange(n)

    #iteramos por cada feature base numerica
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

    if "latitud" in window.columns and "longitud" in window.columns:
        lat_range = window["latitud"].max() - window["latitud"].min()
        lon_range = window["longitud"].max() - window["longitud"].min()
        feats["gps_spread"] = np.sqrt(lat_range**2 + lon_range**2) * 111000

    #metemos nueva feature para deteccion de patrones nocturnos   
    if "timestamp" in window.columns:
        hours = pd.to_datetime(window["timestamp"]).dt.hour.values
        feats["hour_mean"]       = np.mean(hours)
        feats["night_ratio"]     = np.mean((hours >= 22) | (hours <= 5))  # % registros nocturnos
        feats["metro_night_mean"] = np.mean(                              # movimiento nocturno
            window["metros_recorridos"].values[
                (hours >= 22) | (hours <= 5)
            ]
        ) if np.any((hours >= 22) | (hours <= 5)) else 0.0

    return feats


def build_windowed_dataset(df: pd.DataFrame):
    all_feats, all_labels, all_groups = [], [], []

    #agrupamos por animales y creamos ventanas de tiempo.
    for animal_id, group in df.groupby("animal_id"):
        group = group.sort_values("timestamp").reset_index(drop=True)
        n = len(group)
        for start in range(0, n - WINDOW_SIZE + 1, STEP_SIZE):
            window = group.iloc[start : start + WINDOW_SIZE]
            # Usar label dominante de la ventana en lugar del último registro.
            # Evita que ventanas de mastitis se etiqueten como "sana" cuando
            # la progresión todavía no llegó a la fase final.
            label_counts = window["label"].value_counts()
            label = label_counts.index[0]
            all_feats.append(extract_window_features(window))
            all_labels.append(label)
            all_groups.append(animal_id)

    X      = pd.DataFrame(all_feats)
    groups = np.array(all_groups)
    le     = LabelEncoder()
    y      = le.fit_transform(all_labels)

    return X, y, groups, le


# ── Modelo ────────────────────────────────────────────────────────────────────

def make_model() -> Pipeline:
    """Pipeline: imputa NaNs → escala → clasifica."""
    return Pipeline([

        ("imputer", SimpleImputer(strategy="median")), #Completamos posibles datos faltantes
        ("scaler",  StandardScaler()), #Normalizamos
        ("clf",     GradientBoostingClassifier(
            n_estimators=300,      # era 200 → más árboles para 6 clases
            learning_rate=0.07,    # era 0.08 → un poco más conservador
            max_depth=4,
            min_samples_leaf=15,   # era 20 → más flexibilidad por clase
            subsample=0.8,
            random_state=SEED,
        )),
    ])


def train_model(X: pd.DataFrame, y: np.ndarray, groups: np.ndarray):
    """Split 80/20 group-aware → entrena pipeline → devuelve pipeline + sets de test."""
    animals = np.unique(groups)

    # Split estratificado por clase animal — garantiza que cada clase
    # tenga representación en train y test aunque haya pocas vacas.
    # Necesitamos el label_animal para estratificar: tomamos el más frecuente
    # por animal desde y y groups.
    animal_labels = []
    for a in animals:
        mask   = groups == a
        labels = y[mask]
        animal_labels.append(int(pd.Series(labels).mode()[0]))
    animal_labels = np.array(animal_labels)

    train_animals, test_animals = train_test_split(
        animals, test_size=0.2, random_state=SEED,
        stratify=animal_labels   # garantiza al menos 1 animal de mastitis en test
    )
    train_idx = np.isin(groups, train_animals)
    test_idx  = np.isin(groups, test_animals)

    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y[train_idx],       y[test_idx]

    print(f"  Train: {train_idx.sum():,} ventanas ({len(train_animals)} animales)")
    print(f"  Test : {test_idx.sum():,} ventanas ({len(test_animals)} animales)\n")

    pipeline = make_model()
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)

    # Devolvemos X_test sin escalar — plot_diagnostics lo escala internamente
    return pipeline, y_test, y_pred, X_test


# ── Evaluación ────────────────────────────────────────────────────────────────

def evaluate(y_true, y_pred, le):
    labels = le.classes_
    acc    = accuracy_score(y_true, y_pred)
    f1     = f1_score(y_true, y_pred, average="macro")

    print("\n" + "═"*55)
    print("  RESULTADOS (split 80/20)")
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


def print_feature_importance(pipeline: Pipeline, feature_names: list, top_n: int = 15):
    # El modelo vive dentro del pipeline en el paso llamado "clf"
    clf = pipeline.named_steps["clf"]
    imp = pd.Series(clf.feature_importances_, index=feature_names)
    imp = imp.sort_values(ascending=False).head(top_n)
    print(f"\n  Top {top_n} features más importantes:")
    for feat, score in imp.items():
        bar = "█" * int(score / imp.max() * 30)
        print(f"    {feat:45s} {bar} {score:.4f}")


# ── Plots diagnóstico ─────────────────────────────────────────────────────────

def plot_diagnostics(pipeline: Pipeline, le, X_test: pd.DataFrame,
                     y_test: np.ndarray, y_pred: np.ndarray, feature_names: list):
    """
    4 gráficos para entender qué está pasando con los datos y el modelo:
      1. Violinplot de top-4 features por clase  → ¿están solapadas o separadas?
      2. Feature importance                      → ¿qué variables usa el modelo?
      3. Matriz de confusión normalizada         → ¿dónde se equivoca?
      4. Confianza del modelo por clase          → ¿está seguro o dudando?
    """
    # Extraemos el clasificador del pipeline para acceder a feature_importances_
    clf    = pipeline.named_steps["clf"]
    labels = list(le.classes_)
    colors = [LABEL_COLORS.get(l, "#888") for l in labels]
    id2lbl = {i: l for i, l in enumerate(labels)}

    # X_test transformado por el pipeline (imputer + scaler) para predict_proba
    X_test_transformed = pipeline[:-1].transform(X_test)

    fig = plt.figure(figsize=(18, 13))
    fig.suptitle(
        f"Diagnóstico del modelo  |  window = {WINDOW_SIZE} registros "
        f"(~{WINDOW_SIZE * 5 // 60} h por ventana)",
        fontsize=14, fontweight="bold", y=0.99,
    )
    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.40, wspace=0.32)

    # ── Gráfico 1: violinplot de top-4 features normalizadas ──────────────────
    ax1 = fig.add_subplot(gs[0, 0])

    imp  = pd.Series(clf.feature_importances_, index=feature_names)
    top4 = imp.nlargest(4).index.tolist()

    # Usamos X_test sin transformar (valores originales, más legibles)
    df_vis = X_test.copy()
    df_vis["label"] = [id2lbl[i] for i in y_test]

    df_norm = df_vis[top4 + ["label"]].copy()
    for col in top4:
        r = df_norm[col].max() - df_norm[col].min()
        df_norm[col] = (df_norm[col] - df_norm[col].min()) / (r if r > 0 else 1)

    df_melt   = df_norm.melt(id_vars="label", var_name="feature", value_name="valor")
    positions = np.arange(len(top4))
    width     = 0.22

    for i, (label, color) in enumerate(zip(labels, colors)):
        data_by_feat = [
            df_melt[(df_melt["label"] == label) & (df_melt["feature"] == f)]["valor"].values
            for f in top4
        ]
        if any(len(d) == 0 for d in data_by_feat):
            continue
        parts = ax1.violinplot(
            data_by_feat,
            positions + (i - (len(labels) - 1) / 2) * width,
            widths=width * 0.88,
            showmedians=True,
        )
        for pc in parts["bodies"]:
            pc.set_facecolor(color)
            pc.set_alpha(0.60)
        for key in ("cmedians", "cbars", "cmins", "cmaxes"):
            parts[key].set_color(color)

    short = [
        f.replace("temperatura_corporal_prom", "temp")
         .replace("frec_cardiaca_prom", "frec_card")
         .replace("metros_recorridos", "metros")
         .replace("velocidad_movimiento_prom", "velocidad")
         .replace("_mean", "·mean").replace("_std", "·std")
         .replace("_last10", "·last10").replace("_slope", "·slope")
        for f in top4
    ]
    ax1.set_xticks(positions)
    ax1.set_xticklabels(short, fontsize=8)
    ax1.set_ylabel("Valor normalizado [0–1]")
    ax1.set_title("Distribución de top-4 features por clase\n"
                  "Solapamiento alto → problema más difícil (realista)")
    ax1.legend(
        handles=[plt.Rectangle((0,0),1,1, color=c, alpha=0.7) for c in colors],
        labels=labels, fontsize=9, loc="upper right",
    )
    ax1.axhline(0.5, color="gray", linestyle="--", alpha=0.35, linewidth=0.8)
    ax1.grid(axis="y", alpha=0.25)

    # ── Gráfico 2: feature importance horizontal ──────────────────────────────
    ax2 = fig.add_subplot(gs[0, 1])
    imp_top = imp.nlargest(15).sort_values()

    bar_colors = []
    for feat in imp_top.index:
        if "temperatura"              in feat: bar_colors.append("#e74c3c")
        elif "frec"                   in feat: bar_colors.append("#e67e22")
        elif "rmssd" in feat or "sdnn" in feat: bar_colors.append("#9b59b6")
        elif "metros" in feat or "velocidad" in feat: bar_colors.append("#3498db")
        elif "rumia"                  in feat: bar_colors.append("#2ecc71")
        elif "vocal"                  in feat: bar_colors.append("#1abc9c")
        else:                                  bar_colors.append("#95a5a6")

    ax2.barh(range(len(imp_top)), imp_top.values, color=bar_colors, alpha=0.82)
    ax2.set_yticks(range(len(imp_top)))
    ax2.set_yticklabels(
        [f.replace("temperatura_corporal_prom", "temp")
          .replace("frec_cardiaca_prom", "frec_card")
          .replace("metros_recorridos", "metros")
          .replace("velocidad_movimiento_prom", "velocidad")
         for f in imp_top.index],
        fontsize=8,
    )
    ax2.set_xlabel("Importancia (Gini)")
    ax2.set_title("Feature importance — top 15\nColor = grupo fisiológico")
    ax2.grid(axis="x", alpha=0.25)

    grupo_colors = {
        "temperatura": "#e74c3c", "frec. cardíaca": "#e67e22",
        "HRV (rmssd/sdnn)": "#9b59b6", "movimiento": "#3498db",
        "rumia": "#2ecc71", "vocalización": "#1abc9c",
    }
    ax2.legend(
        handles=[plt.Rectangle((0,0),1,1, color=c, alpha=0.8)
                 for c in grupo_colors.values()],
        labels=list(grupo_colors.keys()), fontsize=7, loc="lower right",
    )

    # ── Gráfico 3: matriz de confusión normalizada ────────────────────────────
    ax3 = fig.add_subplot(gs[1, 0])
    cm      = confusion_matrix(y_test, y_pred)
    cm_norm = cm.astype(float) / cm.sum(axis=1, keepdims=True)

    im = ax3.imshow(cm_norm, cmap="RdYlGn", vmin=0, vmax=1)
    plt.colorbar(im, ax=ax3, fraction=0.046, pad=0.04)

    for i in range(len(labels)):
        for j in range(len(labels)):
            ax3.text(
                j, i,
                f"{cm[i,j]}\n({cm_norm[i,j]:.0%})",
                ha="center", va="center", fontsize=10,
                color="black" if cm_norm[i,j] > 0.35 else "white",
            )

    ax3.set_xticks(range(len(labels)))
    ax3.set_yticks(range(len(labels)))
    ax3.set_xticklabels(labels, fontsize=9)
    ax3.set_yticklabels(labels, fontsize=9)
    ax3.set_xlabel("Predicho")
    ax3.set_ylabel("Real")
    ax3.set_title("Matriz de confusión normalizada\nDiagonal verde = correcto  |  Resto = errores")

    # ── Gráfico 4: distribución de probabilidades predichas ───────────────────
    ax4 = fig.add_subplot(gs[1, 1])
    # predict_proba necesita los datos ya transformados por imputer+scaler
    probas = clf.predict_proba(X_test_transformed)
    x_pos  = np.arange(len(labels))
    width4 = 0.25

    for i, (label, color) in enumerate(zip(labels, colors)):
        mask = y_test == i
        if mask.sum() == 0:
            continue
        mean_p = probas[mask].mean(axis=0)
        std_p  = probas[mask].std(axis=0)
        ax4.bar(
            x_pos + (i - 1) * width4, mean_p,
            width=width4 * 0.9, color=color, alpha=0.78,
            label=f"real: {label}",
            yerr=std_p, capsize=3, error_kw={"linewidth": 0.8},
        )

    ax4.set_xticks(x_pos)
    ax4.set_xticklabels([f"P({l})" for l in labels], fontsize=9)
    ax4.set_ylabel("Probabilidad media predicha")
    ax4.set_ylim(0, 1.08)
    ax4.axhline(1 / len(labels), color="gray", linestyle="--",
                alpha=0.45, linewidth=0.8, label="nivel azar")
    ax4.set_title("Confianza del modelo por clase\n"
                  "Barras = media ± std de probabilidades en el test set")
    ax4.legend(fontsize=8)
    ax4.grid(axis="y", alpha=0.25)

    out_path = Path("models/diagnostico.png")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"\n  📊 Plot guardado en: {out_path}")
    plt.show()


def get_next_model_path(base_dir: str = "models/nuevas-clases") -> Path:
    """
    Busca los .pkl existentes en base_dir y devuelve el siguiente path versionado.
    Ej: mastitis_model_v1.pkl → mastitis_model_v2.pkl
    """
    folder = Path(base_dir)
    folder.mkdir(parents=True, exist_ok=True)

    existing = sorted(folder.glob("mastitis_model_v*.pkl"))

    if not existing:
        next_version = 1
    else:
        # Extrae el número de la última versión encontrada
        last = existing[-1].stem          # "mastitis_model_v3"
        last_num = last.rsplit("_v", 1)[-1]
        next_version = int(last_num) + 1

    new_path = folder / f"mastitis_model_v{next_version}.pkl"
    return new_path, next_version, len(existing)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"Cargando {CSV_PATH}...")
    df = pd.read_csv(CSV_PATH, parse_dates=["timestamp"])
    print(f"  {len(df):,} filas | {df['animal_id'].nunique()} animales")
    print(f"  Período: {df['timestamp'].min()} → {df['timestamp'].max()}")
    print(f"\nConstruyendo ventanas deslizantes (window={WINDOW_SIZE}, step={STEP_SIZE})...")

    X, y, groups, le = build_windowed_dataset(df)

    print(f"  → {len(X):,} ventanas | {X.shape[1]} features")

    unique, counts = np.unique(y, return_counts=True)

    print("\n  Distribución de ventanas por clase:")
    for cls_idx, cnt in zip(unique, counts):
        print(f"    {le.classes_[cls_idx]:12s}: {cnt:,} ({cnt/len(y)*100:.1f}%)")

    final_pipeline, y_test, y_pred, X_test = train_model(X, y, groups)

    evaluate(y_test, y_pred, le)
    print_feature_importance(final_pipeline, list(X.columns))

    plot_diagnostics(
        final_pipeline, le,
        X_test, y_test, y_pred,
        list(X.columns),
    )

    model_path, version, prev_count = get_next_model_path()

    artifact = {
        "model":            final_pipeline,
        "label_encoder":    le,
        "feature_names":    list(X.columns),
        "window_size":      WINDOW_SIZE,
        "numeric_features": NUMERIC_FEATURES,
        "bool_features":    BOOL_FEATURES,
        "version":          version,
        "trained_at":       pd.Timestamp.now().isoformat(),
        "classes":          list(le.classes_),
        "n_windows_train":  int((y == y).sum()),   # total ventanas usadas
    }

    with open(model_path, "wb") as f:
        pickle.dump(artifact, f)

    print(f"\n✅ Modelo guardado en : {model_path}")
    print(f"   Versión            : v{version}")
    print(f"   Versiones previas  : {prev_count}")
    print(f"   Clases             : {list(le.classes_)}")
    print("   Para inferencia    : python predict.py")

    print(f"\n✅ Modelo guardado en: {MODEL_PATH}")
    print("   Para inferencia: python predict.py")


if __name__ == "__main__":
    main()