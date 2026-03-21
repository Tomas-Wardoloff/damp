"""
experiment.py
-------------
Experimentación de modelos RNN para detección de mastitis.

Modelos disponibles:
  "lstm"  → RNN con celdas LSTM
  "gru"   → RNN con celdas GRU (más liviana, recomendada para dataset chico)

Uso:
  1. Cambiá MODEL_TYPE abajo
  2. python experiment.py

Requisito:
  pip install torch
"""

from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
import pickle

from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, f1_score, accuracy_score
from sklearn.utils import compute_class_weight

# ╔══════════════════════════════════════════════════════════╗
# ║  CAMBIÁ ESTA VARIABLE PARA PROBAR DISTINTOS MODELOS     ║
# ║  Opciones: "lstm" | "gru"                               ║
# ╚══════════════════════════════════════════════════════════╝
MODEL_TYPE = "lstm"

# ── Configuración ─────────────────────────────────────────────────────────────
CSV_PATH    = "data/damp_data_temporal.csv"
WINDOW_SIZE = 300
STEP_SIZE   = 30
SEED        = 42
PUREZA_MINIMA = 0.80

NUMERIC_FEATURES = [
    "temperatura_corporal_prom",
    "frec_cardiaca_prom",
    "rmssd",
    "sdnn",
    "metros_recorridos",
    "velocidad_movimiento_prom",
]
BOOL_FEATURES = ["hubo_rumia", "hubo_vocalizacion"]
LABEL_COLORS  = {"sana": "#2ecc71", "subclinica": "#f39c12", "clinica": "#e74c3c"}
SEVERIDAD     = {"sana": 0, "subclinica": 1, "clinica": 2}

# ── Hiperparámetros ───────────────────────────────────────────────────────────
HPARAMS = {
    "lstm": {
        "hidden_size":   32,
        "num_layers":    1,
        "dropout":       0.4,
        "epochs":        50,
        "batch_size":    16,
        "learning_rate": 0.0005,
        "patience":      5,
    },
    "gru": {
        "hidden_size":   32,
        "num_layers":    1,
        "dropout":       0.4,
        "epochs":        50,
        "batch_size":    16,
        "learning_rate": 0.0005,
        "patience":      8,
    },
}


# ── Feature Engineering ───────────────────────────────────────────────────────

def extract_window_sequence(window: pd.DataFrame) -> np.ndarray:
    """
    Devuelve la ventana como secuencia 2D (timesteps x features).
    Preserva el orden temporal para que la RNN aprenda patrones secuenciales.
    Shape: (WINDOW_SIZE, n_features)
    """
    return window[NUMERIC_FEATURES + BOOL_FEATURES].values.astype(float)


def build_windowed_dataset(df: pd.DataFrame):
    all_seqs, all_labels, all_groups = [], [], []

    for animal_id, group in df.groupby("animal_id"):
        group = group.sort_values("timestamp").reset_index(drop=True)
        n = len(group)
        for start in range(0, n - WINDOW_SIZE + 1, STEP_SIZE):
            window = group.iloc[start : start + WINDOW_SIZE]

            # Filtramos ventanas muy mixtas — señal ambigua para el modelo
            label_counts   = window["label"].value_counts()
            pureza         = label_counts.iloc[0] / len(window)
            if pureza < PUREZA_MINIMA:
                continue

            label = max(window["label"].unique(), key=lambda l: SEVERIDAD.get(l, 0))
            all_seqs.append(extract_window_sequence(window))
            all_labels.append(label)
            all_groups.append(animal_id)

    X      = np.stack(all_seqs)       # (N, WINDOW_SIZE, n_features)
    groups = np.array(all_groups)
    le     = LabelEncoder()
    y      = le.fit_transform(all_labels)

    return X, y, groups, le


# ── Split ─────────────────────────────────────────────────────────────────────

def split_groups(groups: np.ndarray, y: np.ndarray, test_size: float = 0.15):
    from sklearn.model_selection import GroupShuffleSplit

    animals = np.unique(groups)
    
    gss = GroupShuffleSplit(n_splits=20, test_size=test_size, random_state=SEED)
    
    best_train_idx = None
    best_test_idx = None
    n_classes = len(np.unique(y))

    for train_animals_idx, test_animals_idx in gss.split(animals, groups=animals):
        train_animals = animals[train_animals_idx]
        test_animals  = animals[test_animals_idx]
        
        train_mask = np.isin(groups, train_animals)
        test_mask  = np.isin(groups, test_animals)
        
        clases_train = len(np.unique(y[train_mask]))
        clases_test  = len(np.unique(y[test_mask]))
        
        if clases_train == n_classes and clases_test == n_classes:
            best_train_idx = train_mask
            best_test_idx  = test_mask
            print(f"  Split OK | "
                  f"train={train_mask.sum():,}  test={test_mask.sum():,}")
            print(f"  Clases en train: {np.unique(y[train_mask], return_counts=True)}")
            print(f"  Clases en test : {np.unique(y[test_mask], return_counts=True)}")
            return best_train_idx, best_test_idx

    raise ValueError(
        "No se encontró un split con todas las clases en train Y test. "
        "El dataset puede ser demasiado pequeño o los animales muy homogéneos."
    )


# ── Modelo RNN ────────────────────────────────────────────────────────────────

def build_rnn_model(n_features: int, n_classes: int):
    """
    Arquitectura:
      Input (batch, WINDOW_SIZE, n_features)
        → LSTM/GRU
        → último timestep  ← resume todo el historial
        → Linear(hidden → 64) + ReLU + Dropout
        → Linear(64 → n_classes)
    """
    import torch.nn as nn

    hp = HPARAMS[MODEL_TYPE]

    class MastitisRNN(nn.Module):
        def __init__(self):
            super().__init__()
            rnn_cls  = nn.LSTM if MODEL_TYPE == "lstm" else nn.GRU
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
            return self.head(out[:, -1, :])   # último timestep

    return MastitisRNN()


class RNNDataset:
    def __init__(self, X: np.ndarray, y: np.ndarray):
        import torch
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y = torch.tensor(y, dtype=torch.long)

    def __len__(self):  return len(self.y)
    def __getitem__(self, idx): return self.X[idx], self.y[idx]


# ── Entrenamiento ─────────────────────────────────────────────────────────────

def train_rnn(X: np.ndarray, y: np.ndarray, groups: np.ndarray, n_classes: int):
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader

    hp     = HPARAMS[MODEL_TYPE]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"  Dispositivo: {device}")

    # ── Split train/test por animal ───────────────────────────────────────────
    train_idx, test_idx = split_groups(groups, y)
    X_train_raw, X_test_raw = X[train_idx],  X[test_idx]
    y_train,     y_test     = y[train_idx],   y[test_idx]

    # ── Normalización ─────────────────────────────────────────────────────────
    n_features = X_train_raw.shape[2]
    scaler     = StandardScaler()
    X_train_sc = scaler.fit_transform(
        X_train_raw.reshape(-1, n_features)
    ).reshape(X_train_raw.shape)
    X_test_sc  = scaler.transform(
        X_test_raw.reshape(-1, n_features)
    ).reshape(X_test_raw.shape)

    # Limpieza por si el scaler generó NaN (feature con varianza=0)
    X_train_sc = np.nan_to_num(X_train_sc, nan=0.0, posinf=0.0, neginf=0.0)
    X_test_sc  = np.nan_to_num(X_test_sc,  nan=0.0, posinf=0.0, neginf=0.0)

    # ── Split interno estratificado (train → tr + val) ────────────────────────
    tr_idx, val_idx = train_test_split(
        np.arange(len(X_train_sc)),
        test_size=0.15,
        stratify=y_train,
        random_state=SEED,
    )
    X_tr_sc,  X_val_sc = X_train_sc[tr_idx],  X_train_sc[val_idx]
    y_tr,     y_val    = y_train[tr_idx],      y_train[val_idx]

    print(f"  Clases en tr  : {np.unique(y_tr,  return_counts=True)}")
    print(f"  Clases en val : {np.unique(y_val, return_counts=True)}\n")

    train_loader = DataLoader(RNNDataset(X_tr_sc,  y_tr),  batch_size=hp["batch_size"], shuffle=True)
    val_loader   = DataLoader(RNNDataset(X_val_sc, y_val), batch_size=hp["batch_size"], shuffle=False)

    # ── Modelo, optimizer, loss con pesos de clase ────────────────────────────
    model     = build_rnn_model(n_features, n_classes).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=hp["learning_rate"])
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, factor=0.5, patience=3)

    cw        = compute_class_weight("balanced", classes=np.unique(y_tr), y=y_tr)
    criterion = nn.CrossEntropyLoss(weight=torch.tensor(cw, dtype=torch.float32).to(device))

    # ── Loop de entrenamiento ─────────────────────────────────────────────────
    history          = {"train_loss": [], "val_loss": [], "val_acc": []}
    best_val_loss    = float("inf")
    best_state       = None
    patience_counter = 0

    print(f"  Entrenando {MODEL_TYPE.upper()} — hasta {hp['epochs']} epochs  "
          f"(patience={hp['patience']})\n")

    for epoch in range(1, hp["epochs"] + 1):

        model.train()
        train_loss = 0.0
        for X_b, y_b in train_loader:
            X_b, y_b = X_b.to(device), y_b.to(device)
            optimizer.zero_grad()
            loss = criterion(model(X_b), y_b)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            train_loss += loss.item() * len(y_b)
        train_loss /= len(y_tr)

        model.eval()
        val_loss, val_preds = 0.0, []
        with torch.no_grad():
            for X_b, y_b in val_loader:
                X_b, y_b = X_b.to(device), y_b.to(device)
                logits    = model(X_b)
                val_loss += criterion(logits, y_b).item() * len(y_b)
                val_preds.extend(logits.argmax(dim=1).cpu().numpy())
        val_loss /= len(y_val)
        val_acc   = accuracy_score(y_val, val_preds)

        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["val_acc"].append(val_acc)
        scheduler.step(val_loss)

        mejora = ""
        if val_loss < best_val_loss:
            best_val_loss    = val_loss
            best_state       = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            patience_counter = 0
            mejora           = "  ✓"
        else:
            patience_counter += 1

        print(f"  Epoch {epoch:3d}/{hp['epochs']}  "
              f"train={train_loss:.4f}  val={val_loss:.4f}  acc={val_acc:.4f}{mejora}")

        if patience_counter >= hp["patience"]:
            print(f"\n  ⏹ Early stopping (epoch {epoch})")
            break

    if best_state is not None:
        model.load_state_dict(best_state)
    model.to(device)

    # ── Predicción sobre test ─────────────────────────────────────────────────
    model.eval()
    with torch.no_grad():
        logits_test = model(torch.tensor(X_test_sc, dtype=torch.float32).to(device))
        probas      = torch.softmax(logits_test, dim=1).cpu().numpy()
        y_pred      = logits_test.argmax(dim=1).cpu().numpy()

    return model, scaler, y_test, y_pred, probas, history


# ── Evaluación ────────────────────────────────────────────────────────────────

def evaluate(y_true, y_pred, le):
    # Usamos solo las clases que realmente aparecen en y_true
    clases_presentes = np.unique(np.concatenate([y_true, y_pred]))
    labels_presentes = le.classes_[clases_presentes]

    print("\n" + "═"*55)
    print(f"  RESULTADOS — {MODEL_TYPE.upper()}")
    print("═"*55)
    print(f"  Accuracy : {accuracy_score(y_true, y_pred):.4f}")
    print(f"  F1-macro : {f1_score(y_true, y_pred, average='macro'):.4f}")
    print("\n  Reporte por clase:")
    print(classification_report(
        y_true, y_pred,
        labels=clases_presentes,
        target_names=labels_presentes,
        digits=4
    ))
    cm = confusion_matrix(y_true, y_pred)
    print("  Matriz de confusión:")
    print("         " + "  ".join(f"{l:>10}" for l in labels_presentes))
    for i, row in enumerate(cm):
        print(f"  {labels_presentes[i]:>8} " + "  ".join(f"{v:>10}" for v in row))
    print("═"*55)


# ── Plots ─────────────────────────────────────────────────────────────────────

def plot_history(history):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4))
    fig.suptitle(f"Curva de aprendizaje — {MODEL_TYPE.upper()}", fontsize=13)

    ax1.plot(history["train_loss"], label="train", color="#3498db")
    ax1.plot(history["val_loss"],   label="val",   color="#e74c3c", linestyle="--")
    ax1.set_xlabel("Epoch"); ax1.set_ylabel("Loss")
    ax1.set_title("Loss\nSi val >> train → overfitting")
    ax1.legend(); ax1.grid(alpha=0.25)

    ax2.plot(history["val_acc"], color="#2ecc71")
    ax2.set_xlabel("Epoch"); ax2.set_ylabel("Accuracy")
    ax2.set_title("Accuracy de validación")
    ax2.grid(alpha=0.25)

    plt.tight_layout()
    out = Path(f"models/history_{MODEL_TYPE}.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"  📊 Historial → {out}")
    plt.show()


def plot_confusion_and_proba(y_test, y_pred, probas, le):
    clases_presentes = np.unique(np.concatenate([y_test, y_pred]))
    labels = list(le.classes_[clases_presentes])
    colors = [LABEL_COLORS.get(l, "#888") for l in labels]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle(f"Evaluación — {MODEL_TYPE.upper()}  |  window={WINDOW_SIZE} registros",
                 fontsize=13, fontweight="bold")

    cm      = confusion_matrix(y_test, y_pred)
    cm_norm = cm.astype(float) / cm.sum(axis=1, keepdims=True)
    im = ax1.imshow(cm_norm, cmap="RdYlGn", vmin=0, vmax=1)
    plt.colorbar(im, ax=ax1, fraction=0.046, pad=0.04)
    for i in range(len(labels)):
        for j in range(len(labels)):
            ax1.text(j, i, f"{cm[i,j]}\n({cm_norm[i,j]:.0%})",
                     ha="center", va="center", fontsize=10,
                     color="black" if cm_norm[i,j] > 0.35 else "white")
    ax1.set_xticks(range(len(labels))); ax1.set_yticks(range(len(labels)))
    ax1.set_xticklabels(labels, fontsize=9); ax1.set_yticklabels(labels, fontsize=9)
    ax1.set_xlabel("Predicho"); ax1.set_ylabel("Real")
    ax1.set_title("Matriz de confusión")

    x_pos, w = np.arange(len(labels)), 0.25
    for i, (label, color) in enumerate(zip(labels, colors)):
        mask = y_test == i
        if mask.sum() == 0:
            continue
        ax2.bar(x_pos + (i-1)*w, probas[mask].mean(axis=0),
                width=w*0.9, color=color, alpha=0.78, label=f"real: {label}",
                yerr=probas[mask].std(axis=0), capsize=3,
                error_kw={"linewidth": 0.8})
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels([f"P({l})" for l in labels], fontsize=9)
    ax2.set_ylabel("Probabilidad media"); ax2.set_ylim(0, 1.08)
    ax2.axhline(1/len(labels), color="gray", linestyle="--", alpha=0.45,
                linewidth=0.8, label="nivel azar")
    ax2.set_title("Confianza del modelo por clase")
    ax2.legend(fontsize=8); ax2.grid(axis="y", alpha=0.25)

    plt.tight_layout()
    out = Path(f"models/eval_{MODEL_TYPE}.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"  📊 Evaluación → {out}")
    plt.show()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"Cargando {CSV_PATH}...")
    df = pd.read_csv(CSV_PATH, parse_dates=["timestamp"])
    print(f"  {len(df):,} filas | {df['animal_id'].nunique()} animales")
    print(f"  Período: {df['timestamp'].min()} → {df['timestamp'].max()}")

    # ── Limpieza de NaN ───────────────────────────────────────────────────────
    nans = df.isnull().sum()
    nans = nans[nans > 0]
    if len(nans):
        print(f"\nNaNs detectados:\n{nans}")
    df[NUMERIC_FEATURES] = df.groupby("animal_id")[NUMERIC_FEATURES].transform(
        lambda x: x.fillna(x.median())
    )
    df[NUMERIC_FEATURES] = df[NUMERIC_FEATURES].fillna(df[NUMERIC_FEATURES].median())
    print(f"NaNs después de limpiar: {df.isnull().sum().sum()}")

    # ── Dataset ───────────────────────────────────────────────────────────────
    print(f"\nConstruyendo ventanas (window={WINDOW_SIZE}, step={STEP_SIZE}, "
          f"pureza≥{PUREZA_MINIMA})...")
    X, y, groups, le = build_windowed_dataset(df)
    n_classes = len(le.classes_)

    print("\nDistribución de ventanas:")
    for i, cls in enumerate(le.classes_):
        cnt = (y == i).sum()
        bar = "█" * int(cnt / len(y) * 40)
        print(f"  {cls:12s} (idx={i}): {cnt:5,}  {bar}  {cnt/len(y)*100:.1f}%")

    print(f"\n{'─'*50}")
    print(f"  Modelo  : {MODEL_TYPE.upper()}")
    print(f"  Hparams : {HPARAMS[MODEL_TYPE]}")
    print(f"{'─'*50}\n")

    # ── Entrenamiento ─────────────────────────────────────────────────────────
    Path("models").mkdir(exist_ok=True)
    model, scaler, y_test, y_pred, probas, history = train_rnn(X, y, groups, n_classes)

    # ── Resultados ────────────────────────────────────────────────────────────
    evaluate(y_test, y_pred, le)
    plot_history(history)
    plot_confusion_and_proba(y_test, y_pred, probas, le)

    # ── Guardar ───────────────────────────────────────────────────────────────
    import torch
    rnn_path  = Path(f"models/experiment_{MODEL_TYPE}.pt")
    meta_path = Path(f"models/experiment_{MODEL_TYPE}_meta.pkl")

    torch.save(model.state_dict(), rnn_path)
    with open(meta_path, "wb") as f:
        pickle.dump({
            "scaler":           scaler,
            "label_encoder":    le,
            "window_size":      WINDOW_SIZE,
            "numeric_features": NUMERIC_FEATURES,
            "bool_features":    BOOL_FEATURES,
            "model_type":       MODEL_TYPE,
            "hparams":          HPARAMS[MODEL_TYPE],
            "n_features":       X.shape[2],
            "n_classes":        n_classes,
        }, f)

    print(f"\n✅ Pesos  → {rnn_path}")
    print(f"   Meta   → {meta_path}")


if __name__ == "__main__":
    main()