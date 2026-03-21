"""
exploracion_data.py
═══════════════════
Exploración visual de datos ANTES de entrenar.
Compara dos clases a la vez sobre la línea temporal y sus distribuciones
de features (raw + features de ventana).

Uso rápido:
    python exploracion_data.py

Uso desde código:
    from exploracion_data import run_exploration
    run_exploration(df, pairs=[("sana", "mastitis"), ("sana", "celo")])
"""

from __future__ import annotations
from itertools import combinations
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.collections import LineCollection
from matplotlib.patches import Patch
import numpy as np
import pandas as pd

# ── Constantes (deben coincidir con train.py) ─────────────────────────────────

CSV_PATH    = "data/damp_data_temporal.csv"
OUT_DIR     = "models/nuevas-clases/exploracion"
WINDOW_SIZE = 100          # misma ventana que train.py
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
    "sana":      "#2ecc71",
    "mastitis":  "#e74c3c",
    "celo":      "#9b59b6",
    "febril":    "#e67e22",
    "digestivo": "#1abc9c",
}

# Pares de clases a comparar. Máximo 2 por plot para que sea legible.
DEFAULT_PAIRS = [
    ("sana", "mastitis"),
    ("sana", "celo"),
    ("sana", "febril"),
    ("sana", "digestivo"),
    ("mastitis", "celo"),
    ("mastitis", "febril"),
    ("celo", "febril"),
]


# ── Lógica de features (idéntica a train.py) ──────────────────────────────────

def extract_window_features(window: pd.DataFrame) -> dict:
    feats = {}
    n = len(window)
    x = np.arange(n)

    for col in NUMERIC_FEATURES:
        if col not in window.columns:
            continue
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
        if col not in window.columns:
            continue
        vals = window[col].values.astype(float)
        feats[f"{col}_rate"]   = np.mean(vals)
        feats[f"{col}_last10"] = np.mean(vals[-10:])

    if "latitud" in window.columns and "longitud" in window.columns:
        lat_range = window["latitud"].max() - window["latitud"].min()
        lon_range = window["longitud"].max() - window["longitud"].min()
        feats["gps_spread"] = np.sqrt(lat_range**2 + lon_range**2) * 111000

    if "timestamp" in window.columns:
        hours = pd.to_datetime(window["timestamp"]).dt.hour.values
        feats["hour_mean"]        = np.mean(hours)
        feats["night_ratio"]      = np.mean((hours >= 22) | (hours <= 5))
        if "metros_recorridos" in window.columns:
            night_mask = (hours >= 22) | (hours <= 5)
            feats["metro_night_mean"] = (
                np.mean(window["metros_recorridos"].values[night_mask])
                if night_mask.any() else 0.0
            )

    return feats


def build_windowed_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """
    Construye el dataset de ventanas igual que train.py y devuelve
    un DataFrame con todas las features + columna 'label' y 'animal_id'.
    """
    records = []
    for animal_id, group in df.groupby("animal_id"):
        group = group.sort_values("timestamp").reset_index(drop=True)
        n     = len(group)
        for start in range(0, n - WINDOW_SIZE + 1, STEP_SIZE):
            window      = group.iloc[start : start + WINDOW_SIZE]
            label       = window["label"].value_counts().index[0]
            feats       = extract_window_features(window)
            feats["label"]     = label
            feats["animal_id"] = animal_id
            records.append(feats)

    return pd.DataFrame(records)


# ── Helpers gráficos ──────────────────────────────────────────────────────────

def _label_band(ax, labels_arr: np.ndarray, color_a: str, color_b: str,
                cls_a: str, cls_b: str, alpha: float = 0.18) -> None:
    """Pinta banda de fondo solo para cls_a y cls_b; el resto queda gris claro."""
    n    = len(labels_arr)
    prev = labels_arr[0]
    seg  = 0
    for i in range(1, n + 1):
        cur = labels_arr[i] if i < n else None
        if cur != prev or i == n:
            if prev == cls_a:
                ax.axvspan(seg, i - 1, color=color_a, alpha=alpha, linewidth=0)
            elif prev == cls_b:
                ax.axvspan(seg, i - 1, color=color_b, alpha=alpha, linewidth=0)
            seg = i
        prev = cur
    ax.set_xlim(0, n)


def _colored_line(ax, t: np.ndarray, vals: np.ndarray,
                  labels_arr: np.ndarray,
                  color_a: str, color_b: str,
                  cls_a: str, cls_b: str) -> None:
    """Línea de la serie coloreada por clase; gris para el resto."""
    def _col(lbl):
        if lbl == cls_a:   return color_a
        if lbl == cls_b:   return color_b
        return "#cccccc"

    points = np.array([t, vals]).T.reshape(-1, 1, 2)
    segs   = np.concatenate([points[:-1], points[1:]], axis=1)
    colors = [_col(labels_arr[i]) for i in range(len(t) - 1)]
    lc     = LineCollection(segs, colors=colors, linewidths=0.9, alpha=0.9)
    ax.add_collection(lc)
    ax.autoscale_view()


def _mean_segments(ax, t: np.ndarray, labels_arr: np.ndarray,
                   cls: str, mean_val: float, std_val: float,
                   color: str) -> None:
    """Línea de media ± std por cada segmento continuo de 'cls'."""
    in_seg = False
    seg_s  = 0
    for i in range(len(labels_arr) + 1):
        cur = labels_arr[i] if i < len(labels_arr) else None
        if cur == cls and not in_seg:
            seg_s, in_seg = i, True
        elif cur != cls and in_seg:
            ax.hlines(mean_val, seg_s, i - 1,
                      colors=color, linewidths=2.0, alpha=0.95, zorder=4)
            ax.fill_between(range(seg_s, i),
                            mean_val - std_val, mean_val + std_val,
                            color=color, alpha=0.15, zorder=3)
            in_seg = False


def _short_name(feat: str) -> str:
    return (feat
            .replace("temperatura_corporal_prom", "temp")
            .replace("frec_cardiaca_prom", "frec_card")
            .replace("metros_recorridos", "metros")
            .replace("velocidad_movimiento_prom", "veloc")
            .replace("hubo_", "")
            .replace("_prom", "")
            .replace("_mean", "·μ")
            .replace("_std",  "·σ")
            .replace("_last10", "·l10")
            .replace("_slope", "·slope")
            .replace("_rate", "·rate")
            .replace("_range", "·rng")
            .replace("_", " "))


# ── Plot principal: contraste de 2 clases ─────────────────────────────────────

def plot_pair_contrast(
    df_raw: pd.DataFrame,
    df_win: pd.DataFrame,
    cls_a: str,
    cls_b: str,
    animal_id: str | None = None,
    out_dir: str = OUT_DIR,
) -> None:
    """
    Dashboard de contraste entre cls_a y cls_b. Máximo 2 clases por plot.

    Estructura:
      Fila 0  — Banda de timeline (toda la serie del animal)
      Filas 1..N — Una fila por feature raw:
                   · Serie temporal (col ancha) coloreada por las 2 clases
                   · Violin de distribución de valores raw por clase (col angosta)
      Última fila — Heatmap de solapamiento de features de ventana entre las 2 clases

    Parámetros
    ----------
    df_raw   : DataFrame original (una fila = un registro de 5 min)
    df_win   : DataFrame de ventanas construido por build_windowed_dataset()
    cls_a    : primera clase a comparar
    cls_b    : segunda clase a comparar
    animal_id: si se pasa, filtra solo ese animal; si es None usa todos
    out_dir  : carpeta de salida
    """
    color_a = LABEL_COLORS.get(cls_a, "#555")
    color_b = LABEL_COLORS.get(cls_b, "#999")

    Path(out_dir).mkdir(parents=True, exist_ok=True)

    # ── Filtrar datos ─────────────────────────────────────────────────────────
    if animal_id:
        raw = (df_raw[df_raw["animal_id"] == animal_id]
               .sort_values("timestamp").reset_index(drop=True))
        win = df_win[df_win["animal_id"] == animal_id].copy()
        title_suffix = f"Animal: {animal_id}"
    else:
        # Tomar el primer animal que tenga AMBAS clases (más representativo)
        raw, win = _find_best_animal(df_raw, df_win, cls_a, cls_b)
        title_suffix = f"Animal: {raw['animal_id'].iloc[0]}"

    labels_arr = raw["label"].values
    n          = len(raw)
    t          = np.arange(n)

    # Solo filas que pertenecen a una de las dos clases (para los violines)
    mask_a_raw = labels_arr == cls_a
    mask_b_raw = labels_arr == cls_b
    mask_a_win = win["label"] == cls_a
    mask_b_win = win["label"] == cls_b

    # Features raw disponibles
    raw_feats = [f for f in NUMERIC_FEATURES + BOOL_FEATURES
                 if f in raw.columns]

    # ── Layout ────────────────────────────────────────────────────────────────
    n_feat_rows = len(raw_feats)
    n_rows      = 1 + n_feat_rows + 1          # timeline + feats + heatmap
    fig = plt.figure(figsize=(22, 2.6 * n_rows + 1))
    fig.suptitle(
        f"Contraste de clases:  [{cls_a}]  vs  [{cls_b}]  —  {title_suffix}\n"
        f"Ventana: {WINDOW_SIZE} registros (~{WINDOW_SIZE * 5 // 60}h)  ·  "
        f"Step: {STEP_SIZE}",
        fontsize=13, fontweight="bold", y=1.005,
    )
    gs = gridspec.GridSpec(
        n_rows, 2, figure=fig,
        width_ratios=[3.2, 1],
        hspace=0.07,
        wspace=0.20,
    )

    # ── Fila 0: timeline de estados ───────────────────────────────────────────
    ax_top = fig.add_subplot(gs[0, 0])
    _label_band(ax_top, labels_arr, color_a, color_b, cls_a, cls_b, alpha=0.55)
    ax_top.set_yticks([])
    ax_top.set_xlim(0, n)
    ax_top.set_xticklabels([])
    ax_top.set_title(
        f"Timeline de estados  ·  [{cls_a}]  vs  [{cls_b}]  "
        f"(gris = otras clases)",
        fontsize=9, pad=5,
    )
    legend_patches = [
        Patch(color=color_a, alpha=0.75, label=cls_a),
        Patch(color=color_b, alpha=0.75, label=cls_b),
        Patch(color="#cccccc", alpha=0.75, label="otras clases"),
    ]
    ax_top.legend(handles=legend_patches, fontsize=8, ncol=3,
                  loc="upper right", framealpha=0.9)

    # col derecha fila 0: vacía (leyenda sola)
    ax_leg = fig.add_subplot(gs[0, 1])
    ax_leg.axis("off")
    ax_leg.text(0.5, 0.5,
                f"n={mask_a_raw.sum():,} reg [{cls_a}]\n"
                f"n={mask_b_raw.sum():,} reg [{cls_b}]\n\n"
                f"ventanas [{cls_a}]: {mask_a_win.sum()}\n"
                f"ventanas [{cls_b}]: {mask_b_win.sum()}",
                ha="center", va="center", fontsize=8,
                color="#555", transform=ax_leg.transAxes)

    # ── Filas 1..N: una por feature raw ──────────────────────────────────────
    for row_i, feat in enumerate(raw_feats, start=1):
        vals      = raw[feat].values.astype(float)
        is_last_f = row_i == n_feat_rows

        mean_a = vals[mask_a_raw].mean() if mask_a_raw.any() else np.nan
        std_a  = vals[mask_a_raw].std()  if mask_a_raw.any() else 0.0
        mean_b = vals[mask_b_raw].mean() if mask_b_raw.any() else np.nan
        std_b  = vals[mask_b_raw].std()  if mask_b_raw.any() else 0.0

        # ── Serie temporal ────────────────────────────────────────────────
        ax_s = fig.add_subplot(gs[row_i, 0], sharex=ax_top)
        _label_band(ax_s, labels_arr, color_a, color_b, cls_a, cls_b, alpha=0.10)
        _colored_line(ax_s, t, vals, labels_arr, color_a, color_b, cls_a, cls_b)

        if mask_a_raw.any():
            _mean_segments(ax_s, t, labels_arr, cls_a, mean_a, std_a, color_a)
        if mask_b_raw.any():
            _mean_segments(ax_s, t, labels_arr, cls_b, mean_b, std_b, color_b)

        # Anotación de medias
        delta = abs(mean_a - mean_b) if not (np.isnan(mean_a) or np.isnan(mean_b)) else 0
        ax_s.set_ylabel(_short_name(feat), fontsize=8, rotation=0,
                        ha="right", va="center", labelpad=52)
        ax_s.yaxis.set_major_locator(plt.MaxNLocator(4))
        ax_s.tick_params(axis="y", labelsize=7)
        ax_s.grid(axis="y", alpha=0.15, linewidth=0.5)
        ax_s.spines[["top", "right"]].set_visible(False)

        if not is_last_f:
            plt.setp(ax_s.get_xticklabels(), visible=False)
        else:
            ax_s.set_xlabel("Registro (índice temporal)", fontsize=8)
            ax_s.tick_params(axis="x", labelsize=7)

        # ── Violin de distribución por clase ──────────────────────────────
        ax_v = fig.add_subplot(gs[row_i, 1])

        data_plot = []
        colors_v  = []
        labels_v  = []
        for cls, mask, col in [(cls_a, mask_a_raw, color_a),
                               (cls_b, mask_b_raw, color_b)]:
            d = vals[mask]
            if len(d) > 1:
                data_plot.append(d)
                colors_v.append(col)
                labels_v.append(cls)

        positions_v = list(range(len(data_plot)))

        if len(data_plot) >= 1:
            parts = ax_v.violinplot(data_plot, positions=positions_v,
                                    widths=0.55, showmedians=True,
                                    showextrema=False)
            for pc, col in zip(parts["bodies"], colors_v):
                pc.set_facecolor(col)
                pc.set_alpha(0.55)
            parts["cmedians"].set_colors(colors_v)
            parts["cmedians"].set_linewidth(2.0)

            for pos, d, col in zip(positions_v, data_plot, colors_v):
                ax_v.scatter(pos, np.mean(d), color=col, s=28,
                             zorder=5, edgecolors="white", linewidths=0.6)

            if len(data_plot) == 2:
                ax_v.annotate(
                    f"Δμ = {delta:.2f}",
                    xy=(0.5, 0.97), xycoords="axes fraction",
                    ha="center", va="top", fontsize=7,
                    color="#555",
                )

        # ticks siempre alineados con los datos reales disponibles
        ax_v.set_xticks(positions_v)
        ax_v.set_xticklabels(labels_v, fontsize=7)
        ax_v.yaxis.set_major_locator(plt.MaxNLocator(4))
        ax_v.tick_params(axis="y", labelsize=7)
        ax_v.grid(axis="y", alpha=0.15, linewidth=0.5)
        ax_v.spines[["top", "right"]].set_visible(False)
        if row_i == 1:
            ax_v.set_title("Distribución\npor clase", fontsize=8, pad=4)

    # ── Última fila: heatmap de solapamiento en features de ventana ───────────
    ax_heat = fig.add_subplot(gs[n_rows - 1, :])
    _plot_window_feature_overlap(ax_heat, win, cls_a, cls_b, color_a, color_b)

    # ── Guardar ───────────────────────────────────────────────────────────────
    suffix = f"_{animal_id}" if animal_id else "_global"
    fname  = f"contraste_{cls_a}_vs_{cls_b}{suffix}.png"
    out    = Path(out_dir) / fname
    plt.savefig(out, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"  Guardado: {out}")


def _plot_window_feature_overlap(
    ax,
    win: pd.DataFrame,
    cls_a: str,
    cls_b: str,
    color_a: str,
    color_b: str,
) -> None:
    """
    Barras horizontales de solapamiento por feature de ventana.
    Cada barra muestra la diferencia normalizada de medias (effect size simple).
    Una barra larga y de un solo color = buena separación.
    Una barra corta o centrada = clases muy solapadas en esa feature.
    """
    mask_a = win["label"] == cls_a
    mask_b = win["label"] == cls_b

    win_feats = [c for c in win.columns if c not in ("label", "animal_id")]

    rows = []
    for feat in win_feats:
        vals_a = win.loc[mask_a, feat].dropna().values
        vals_b = win.loc[mask_b, feat].dropna().values
        if len(vals_a) < 2 or len(vals_b) < 2:
            continue
        mu_a, mu_b = vals_a.mean(), vals_b.mean()
        pooled_std = np.sqrt((vals_a.std()**2 + vals_b.std()**2) / 2) + 1e-9
        effect     = (mu_a - mu_b) / pooled_std   # Cohen's d simplificado
        rows.append({"feat": feat, "effect": effect, "mu_a": mu_a, "mu_b": mu_b})

    if not rows:
        ax.axis("off")
        return

    df_eff = (pd.DataFrame(rows)
              .assign(abs_effect=lambda d: d["effect"].abs())
              .sort_values("abs_effect", ascending=True))

    # Mostrar top 20 para que sea legible
    df_eff = df_eff.tail(20)

    colors_bar = [color_a if e > 0 else color_b for e in df_eff["effect"]]
    bars = ax.barh(range(len(df_eff)), df_eff["effect"], color=colors_bar,
                   alpha=0.72, edgecolor="white", linewidth=0.4)

    ax.set_yticks(range(len(df_eff)))
    ax.set_yticklabels([_short_name(f) for f in df_eff["feat"]], fontsize=7)
    ax.axvline(0, color="#888", linewidth=0.8, linestyle="--")
    ax.axvline( 0.5, color="#bbb", linewidth=0.5, linestyle=":")
    ax.axvline(-0.5, color="#bbb", linewidth=0.5, linestyle=":")
    ax.set_xlabel("Cohen's d  (positivo → mayor en clase izquierda)", fontsize=8)
    ax.set_title(
        f"Separabilidad de features de ventana  ·  {cls_a} (←)  vs  {cls_b} (→)\n"
        "Barras más largas = mejor discriminación  ·  Top 20 features ordenadas por separabilidad",
        fontsize=8, pad=5,
    )
    ax.grid(axis="x", alpha=0.2, linewidth=0.5)
    ax.spines[["top", "right"]].set_visible(False)

    legend_patches = [
        Patch(color=color_a, alpha=0.72, label=f"mayor en {cls_a}"),
        Patch(color=color_b, alpha=0.72, label=f"mayor en {cls_b}"),
    ]
    ax.legend(handles=legend_patches, fontsize=7, loc="lower right")


def _find_best_animal(
    df_raw: pd.DataFrame,
    df_win: pd.DataFrame,
    cls_a: str,
    cls_b: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Devuelve el animal que tiene registros de AMBAS clases y mayor cantidad combinada.
    Si ningún animal tiene las dos clases, usa el que tenga al menos una.
    """
    # Candidatos que tienen al menos 1 registro de cada clase
    has_a = set(df_raw[df_raw["label"] == cls_a]["animal_id"].unique())
    has_b = set(df_raw[df_raw["label"] == cls_b]["animal_id"].unique())
    both  = has_a & has_b

    if both:
        # Entre los que tienen las dos, elegir el de mayor cobertura combinada
        mask   = df_raw["label"].isin([cls_a, cls_b]) & df_raw["animal_id"].isin(both)
        counts = df_raw[mask].groupby("animal_id").size()
    else:
        # Fallback: cualquier animal con al menos una de las dos clases
        mask   = df_raw["label"].isin([cls_a, cls_b])
        counts = df_raw[mask].groupby("animal_id").size()

    if counts.empty:
        raise ValueError(f"No hay animales con las clases {cls_a} o {cls_b}")

    best = counts.idxmax()
    raw  = (df_raw[df_raw["animal_id"] == best]
            .sort_values("timestamp").reset_index(drop=True))
    win  = df_win[df_win["animal_id"] == best].copy()
    return raw, win


# ── Función principal de exploración ──────────────────────────────────────────

def run_exploration(
    df: pd.DataFrame,
    pairs: list[tuple[str, str]] | None = None,
    animal_id: str | None = None,
    out_dir: str = OUT_DIR,
) -> None:
    """
    Genera un plot de contraste por cada par de clases.

    Parámetros
    ----------
    df        : DataFrame original cargado desde el CSV
    pairs     : lista de tuplas (cls_a, cls_b). Si es None, usa DEFAULT_PAIRS
                filtrando solo los pares que tengan datos en df.
    animal_id : si se pasa, todos los plots se hacen para ese animal.
                Si es None, se selecciona automáticamente el mejor animal por par.
    out_dir   : carpeta de salida de los PNG
    """
    if pairs is None:
        pairs = DEFAULT_PAIRS

    classes_in_data = set(df["label"].unique())

    # Filtrar pares que no tienen datos
    pairs_ok = [
        (a, b) for a, b in pairs
        if a in classes_in_data and b in classes_in_data
    ]
    if not pairs_ok:
        print("  ⚠️  Ninguno de los pares solicitados tiene datos en el DataFrame.")
        return

    print(f"\n  Construyendo dataset de ventanas (window={WINDOW_SIZE}, step={STEP_SIZE})...")
    df_win = build_windowed_dataset(df)
    print(f"  → {len(df_win):,} ventanas · {df_win.shape[1] - 2} features de ventana")

    print(f"\n  Generando {len(pairs_ok)} plots de contraste → {out_dir}/\n")
    for cls_a, cls_b in pairs_ok:
        print(f"  [{cls_a}] vs [{cls_b}]")
        try:
            plot_pair_contrast(df, df_win, cls_a, cls_b,
                               animal_id=animal_id, out_dir=out_dir)
        except Exception as e:
            print(f"    ⚠️  Error: {e}")

    print(f"\n  ✅ Exploración completa. Plots en: {out_dir}/")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Cargando {CSV_PATH}...")
    df = pd.read_csv(CSV_PATH, parse_dates=["timestamp"])
    print(f"  {len(df):,} filas  ·  {df['animal_id'].nunique()} animales")
    print(f"  Clases presentes: {sorted(df['label'].unique())}")

    run_exploration(df)