"""
explore_windows.py
──────────────────
Exploración visual del pipeline de feature engineering del modelo de mastitis.
Genera plots comparativos entre vacas mostrando cómo se construyen las ventanas
y cómo se asignan los labels en contraste con el timeline de cada animal.

Uso:
    python explore_windows.py
    python explore_windows.py --csv data/damp_data_temporal.csv
    python explore_windows.py --animal 1042 1055       # filtrar vacas específicas
    python explore_windows.py --out mi_carpeta/        # cambiar directorio de salida
"""

import argparse
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.collections import LineCollection
from matplotlib.ticker import MaxNLocator
import matplotlib.dates as mdates

# ─── Mismos parámetros que el modelo ────────────────────────────────────────
CSV_PATH    = "data/damp_data_temporal.csv"
WINDOW_SIZE = 80
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
    "sana":       "#2ecc71",
    "mastitis":   "#e74c3c",
    "celo":       "#9b59b6",
    "febril":     "#e67e22",
    "digestivo":  "#1abc9c",
}
UNKNOWN_COLOR = "#95a5a6"

# ─── Feature engineering (idéntico al modelo) ────────────────────────────────

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

    if "latitud" in window.columns and "longitud" in window.columns:
        lat_range = window["latitud"].max() - window["latitud"].min()
        lon_range = window["longitud"].max() - window["longitud"].min()
        feats["gps_spread"] = np.sqrt(lat_range**2 + lon_range**2) * 111000

    if "timestamp" in window.columns:
        hours = pd.to_datetime(window["timestamp"]).dt.hour.values
        feats["hour_mean"]        = np.mean(hours)
        feats["night_ratio"]      = np.mean((hours >= 22) | (hours <= 5))
        feats["metro_night_mean"] = np.mean(
            window["metros_recorridos"].values[(hours >= 22) | (hours <= 5)]
        ) if np.any((hours >= 22) | (hours <= 5)) else 0.0

    return feats


def build_windowed_dataset(df: pd.DataFrame):
    """Genera las ventanas con su label dominante — igual que en train."""
    records = []
    for animal_id, group in df.groupby("animal_id"):
        group = group.sort_values("timestamp").reset_index(drop=True)
        n = len(group)
        for start in range(0, n - WINDOW_SIZE + 1, STEP_SIZE):
            window = group.iloc[start: start + WINDOW_SIZE]
            label_counts = window["label"].value_counts()
            dominant_label = label_counts.index[0]
            label_dist     = label_counts / label_counts.sum()  # distribución

            feats = extract_window_features(window)
            feats["animal_id"]      = animal_id
            feats["window_start"]   = window["timestamp"].iloc[0]
            feats["window_end"]     = window["timestamp"].iloc[-1]
            feats["window_center"]  = window["timestamp"].iloc[WINDOW_SIZE // 2]
            feats["label"]          = dominant_label
            feats["label_purity"]   = label_dist.iloc[0]  # fracción del label dominante
            feats["label_n_unique"] = label_counts.nunique()
            records.append(feats)

    return pd.DataFrame(records)


# ─── Helpers de plot ─────────────────────────────────────────────────────────

def label_color(lbl):
    return LABEL_COLORS.get(str(lbl).lower(), UNKNOWN_COLOR)


def _fmt_feature(name: str) -> str:
    return (name
            .replace("temperatura_corporal_prom", "Temp corporal")
            .replace("frec_cardiaca_prom",         "Frec. cardíaca")
            .replace("metros_recorridos",           "Metros recorridos")
            .replace("velocidad_movimiento_prom",   "Velocidad mov.")
            .replace("_mean",   " (mean)")
            .replace("_std",    " (std)")
            .replace("_slope",  " (slope)")
            .replace("_last10", " (last10)")
            .replace("_range",  " (range)")
            )


def add_label_background(ax, times, labels, alpha=0.12):
    """Colorea el fondo del eje según el label real en cada timestamp."""
    if len(times) == 0:
        return
    prev_lbl = labels[0]
    seg_start = times[0]
    for t, lbl in zip(times[1:], labels[1:]):
        if lbl != prev_lbl:
            ax.axvspan(seg_start, t,
                       color=label_color(prev_lbl), alpha=alpha, linewidth=0)
            seg_start = t
            prev_lbl  = lbl
    ax.axvspan(seg_start, times[-1],
               color=label_color(prev_lbl), alpha=alpha, linewidth=0)


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 1 — Timeline completo de cada animal
# ═══════════════════════════════════════════════════════════════════════════════

def plot_animal_timelines(df: pd.DataFrame, animals: list, out_dir: Path):
    """
    Para cada vaca: panel con las señales numéricas + banda de color según label real
    + marcas verticales mostrando dónde caen las ventanas y qué label se le asignó.
    """
    feats_to_plot = [
        "temperatura_corporal_prom",
        "frec_cardiaca_prom",
        "metros_recorridos",
        "rmssd",
    ]

    for animal_id in animals:
        adf = df[df["animal_id"] == animal_id].sort_values("timestamp").copy()
        if len(adf) < WINDOW_SIZE:
            print(f"  ⚠ Animal {animal_id}: sólo {len(adf)} registros, se omite.")
            continue

        # Construir ventanas sólo para este animal
        records = []
        n = len(adf)
        adf_reset = adf.reset_index(drop=True)
        for start in range(0, n - WINDOW_SIZE + 1, STEP_SIZE):
            window   = adf_reset.iloc[start: start + WINDOW_SIZE]
            lbl_cnt  = window["label"].value_counts()
            dom_lbl  = lbl_cnt.index[0]
            purity   = lbl_cnt.iloc[0] / lbl_cnt.sum()
            records.append({
                "t_start":  window["timestamp"].iloc[0],
                "t_end":    window["timestamp"].iloc[-1],
                "t_center": window["timestamp"].iloc[WINDOW_SIZE // 2],
                "label":    dom_lbl,
                "purity":   purity,
            })
        wins = pd.DataFrame(records)

        times  = adf["timestamp"].values
        labels = adf["label"].values

        n_feats = len(feats_to_plot)
        fig, axes = plt.subplots(
            n_feats + 1, 1,
            figsize=(16, 3.5 * (n_feats + 1)),
            sharex=True,
        )
        fig.suptitle(
            f"Animal {animal_id}  |  {len(adf):,} registros  |  "
            f"{int(len(wins))} ventanas (w={WINDOW_SIZE}, step={STEP_SIZE})",
            fontsize=13, fontweight="bold", y=1.001,
        )

        # ── Panel superior: label real + ventanas asignadas ──────────────────
        ax0 = axes[0]
        ax0.set_yticks([])
        ax0.set_title("Labels reales (fondo) vs label asignado por ventana (triángulos)", fontsize=9)

        # Fondo con label real
        add_label_background(ax0, times, labels, alpha=0.45)

        # Ventanas: línea de duración + triángulo coloreado por label dominante
        for _, w in wins.iterrows():
            c = label_color(w["label"])
            ax0.plot(
                [w["t_start"], w["t_end"]], [0.5, 0.5],
                color=c, linewidth=2.5, alpha=0.55, solid_capstyle="round",
            )
            ax0.plot(
                w["t_center"], 0.5,
                marker="^", color=c, markersize=8,
                markeredgecolor="white", markeredgewidth=0.6,
                alpha=0.9,
            )
            # Pureza de label dentro de la ventana
            if w["purity"] < 0.85:
                ax0.text(
                    w["t_center"], 0.62,
                    f"{w['purity']:.0%}",
                    ha="center", va="bottom", fontsize=5.5,
                    color=c, fontweight="bold",
                )

        ax0.set_ylim(0, 1)

        # Leyenda
        handles = [mpatches.Patch(color=v, label=k) for k, v in LABEL_COLORS.items()]
        ax0.legend(handles=handles, loc="upper right",
                   fontsize=8, ncol=len(LABEL_COLORS))

        # ── Paneles de señales numéricas ─────────────────────────────────────
        for i, feat in enumerate(feats_to_plot):
            if feat not in adf.columns:
                continue
            ax = axes[i + 1]
            vals = adf[feat].values.astype(float)

            # Fondo label real
            add_label_background(ax, times, labels)

            # Línea de la señal coloreada por label
            segs  = []
            colors_seg = []
            for j in range(len(times) - 1):
                segs.append([(times[j], vals[j]), (times[j+1], vals[j+1])])
                colors_seg.append(label_color(labels[j]))
            lc = LineCollection(segs, colors=colors_seg, linewidth=1.0, alpha=0.85)
            ax.add_collection(lc)
            ax.set_xlim(times[0], times[-1])
            ax.set_ylim(np.nanmin(vals) * 0.98, np.nanmax(vals) * 1.02)

            # Medias por ventana (puntos)
            feat_mean_key = f"{feat}_mean"
            if feat_mean_key in pd.DataFrame(
                [extract_window_features(adf_reset.iloc[0: WINDOW_SIZE])]).columns:
                for _, w in wins.iterrows():
                    mask_w = (adf["timestamp"] >= w["t_start"]) & \
                             (adf["timestamp"] <= w["t_end"])
                    mean_v = adf.loc[mask_w, feat].mean()
                    ax.plot(
                        w["t_center"], mean_v,
                        "D", color=label_color(w["label"]),
                        markersize=5, alpha=0.7,
                        markeredgecolor="white", markeredgewidth=0.5,
                    )

            ax.set_ylabel(_fmt_feature(feat), fontsize=8)
            ax.grid(axis="y", alpha=0.2)
            ax.yaxis.set_major_locator(MaxNLocator(4))

        # Formato eje X
        axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%d-%b\n%H:%M"))
        axes[-1].xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.setp(axes[-1].xaxis.get_majorticklabels(), fontsize=7)

        plt.tight_layout()
        fpath = out_dir / f"timeline_animal_{animal_id}.png"
        plt.savefig(fpath, dpi=140, bbox_inches="tight")
        plt.close()
        print(f"  ✅ {fpath}")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 2 — Comparativa de features entre vacas (ventanas)
# ═══════════════════════════════════════════════════════════════════════════════

def plot_feature_comparison(wins_df: pd.DataFrame, out_dir: Path):
    """
    Heatmap temporal de features agregadas por ventana para cada vaca,
    lado a lado, con la barra de label dominante encima.
    """
    feat_cols = [
        "temperatura_corporal_prom_mean",
        "frec_cardiaca_prom_mean",
        "metros_recorridos_mean",
        "rmssd_mean",
        "sdnn_mean",
        "velocidad_movimiento_prom_mean",
        "hubo_rumia_rate",
        "hubo_vocalizacion_rate",
        "night_ratio",
    ]
    feat_cols = [c for c in feat_cols if c in wins_df.columns]
    animals   = sorted(wins_df["animal_id"].unique())
    n_animals = len(animals)

    if n_animals == 0:
        print("  ⚠ Sin animales para comparar.")
        return

    fig, axes = plt.subplots(
        len(feat_cols) + 1, n_animals,
        figsize=(max(4, 3.5 * n_animals), 2.8 * (len(feat_cols) + 1)),
        squeeze=False,
    )
    fig.suptitle(
        "Comparativa de features por ventana entre animales\n"
        "(cada columna = una vaca | cada fila = un feature | color superior = label dominante)",
        fontsize=12, fontweight="bold", y=1.002,
    )

    for col_i, animal_id in enumerate(animals):
        adf = wins_df[wins_df["animal_id"] == animal_id].copy()
        adf = adf.sort_values("window_center").reset_index(drop=True)
        n_wins = len(adf)
        x_idx  = np.arange(n_wins)

        # ── Banda de label ────────────────────────────────────────────────────
        ax_top = axes[0][col_i]
        for i, row in adf.iterrows():
            ax_top.barh(
                0, 1, left=i, height=1,
                color=label_color(row["label"]),
                alpha=max(0.3, row["label_purity"]),
            )
        ax_top.set_xlim(0, n_wins)
        ax_top.set_yticks([])
        ax_top.set_title(f"Animal {animal_id}\n({n_wins} ventanas)", fontsize=9)
        ax_top.set_xticks([])
        if col_i == 0:
            ax_top.set_ylabel("Label\ndominante", fontsize=7)

        # ── Heatmap de cada feature ───────────────────────────────────────────
        for row_i, feat in enumerate(feat_cols):
            ax = axes[row_i + 1][col_i]
            if feat not in adf.columns or adf[feat].isna().all():
                ax.set_visible(False)
                continue

            vals = adf[feat].values.astype(float)
            # Normalizar por animal para comparación visual
            v_min, v_max = np.nanmin(vals), np.nanmax(vals)
            v_range = v_max - v_min if v_max != v_min else 1.0
            norm_vals = (vals - v_min) / v_range

            ax.imshow(
                norm_vals.reshape(1, -1),
                aspect="auto", cmap="RdYlGn",
                vmin=0, vmax=1,
                interpolation="nearest",
            )

            # Superponer marcas de cambio de label
            for i in range(1, len(adf)):
                if adf["label"].iloc[i] != adf["label"].iloc[i - 1]:
                    ax.axvline(i - 0.5, color="white", linewidth=1.5, alpha=0.9)

            # Valor real en texto si pocas ventanas
            if n_wins <= 30:
                for xi, v in enumerate(vals):
                    ax.text(xi, 0, f"{v:.1f}",
                            ha="center", va="center",
                            fontsize=4.5, color="black")

            ax.set_xticks([])
            ax.set_yticks([])
            if col_i == 0:
                ax.set_ylabel(_fmt_feature(feat), fontsize=7, labelpad=2)

    plt.tight_layout()
    fpath = out_dir / "comparativa_features_vacas.png"
    plt.savefig(fpath, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"  ✅ {fpath}")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 3 — Pureza de label por ventana (¿cuánto se mezclan las clases?)
# ═══════════════════════════════════════════════════════════════════════════════

def plot_label_purity(wins_df: pd.DataFrame, out_dir: Path):
    """
    Scatter: eje X = tiempo de la ventana, eje Y = pureza del label dominante.
    Color = label dominante. Una vaca por subplot.
    Muestra dónde hay transiciones ambiguas entre estados.
    """
    animals = sorted(wins_df["animal_id"].unique())
    n = len(animals)
    ncols = min(3, n)
    nrows = int(np.ceil(n / ncols))

    fig, axes = plt.subplots(
        nrows, ncols,
        figsize=(6 * ncols, 3.5 * nrows),
        squeeze=False,
    )
    fig.suptitle(
        "Pureza del label dominante por ventana\n"
        "Puntos bajos = ventanas con mezcla de clases (transiciones)",
        fontsize=12, fontweight="bold",
    )

    for idx, animal_id in enumerate(animals):
        row, col = divmod(idx, ncols)
        ax = axes[row][col]

        adf = wins_df[wins_df["animal_id"] == animal_id].sort_values("window_center")
        for lbl, grp in adf.groupby("label"):
            ax.scatter(
                grp["window_center"], grp["label_purity"],
                c=label_color(lbl), label=lbl,
                s=35, alpha=0.75, edgecolors="white", linewidths=0.4,
            )

        ax.axhline(0.85, color="gray", linestyle="--",
                   linewidth=0.8, alpha=0.5, label="85% pureza")
        ax.set_ylim(0, 1.05)
        ax.set_title(f"Animal {animal_id}", fontsize=9)
        ax.set_ylabel("Pureza", fontsize=8)
        ax.grid(alpha=0.2)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
        plt.setp(ax.xaxis.get_majorticklabels(), fontsize=6, rotation=30)
        ax.legend(fontsize=6, loc="lower right")

    # Ocultar ejes vacíos
    for idx in range(len(animals), nrows * ncols):
        row, col = divmod(idx, ncols)
        axes[row][col].set_visible(False)

    plt.tight_layout()
    fpath = out_dir / "pureza_labels_por_ventana.png"
    plt.savefig(fpath, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"  ✅ {fpath}")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 4 — Distribución de features por label (violinplot global)
# ═══════════════════════════════════════════════════════════════════════════════

def plot_feature_by_label(wins_df: pd.DataFrame, out_dir: Path):
    """
    Para cada feature clave: violinplot separado por label.
    Permite ver si el feature discrimina bien entre clases.
    """
    feat_cols = [
        "temperatura_corporal_prom_mean",
        "frec_cardiaca_prom_mean",
        "metros_recorridos_mean",
        "rmssd_mean",
        "sdnn_mean",
        "velocidad_movimiento_prom_mean",
        "hubo_rumia_rate",
        "night_ratio",
    ]
    feat_cols = [c for c in feat_cols if c in wins_df.columns]
    labels    = sorted(wins_df["label"].dropna().unique())
    colors    = [label_color(l) for l in labels]

    ncols = 2
    nrows = int(np.ceil(len(feat_cols) / ncols))
    fig, axes = plt.subplots(
        nrows, ncols,
        figsize=(10, 4 * nrows),
        squeeze=False,
    )
    fig.suptitle(
        "Distribución de features por clase (todas las vacas)\n"
        "Solapamiento alto = feature poco discriminativo para esa clase",
        fontsize=12, fontweight="bold",
    )

    for idx, feat in enumerate(feat_cols):
        row, col = divmod(idx, ncols)
        ax = axes[row][col]

        data_by_label = [
            wins_df.loc[wins_df["label"] == lbl, feat].dropna().values
            for lbl in labels
        ]
        valid = [(d, l, c) for d, l, c in zip(data_by_label, labels, colors) if len(d) > 1]
        if not valid:
            ax.set_visible(False)
            continue

        parts = ax.violinplot(
            [v[0] for v in valid],
            positions=range(len(valid)),
            showmedians=True,
            showextrema=True,
        )
        for i, pc in enumerate(parts["bodies"]):
            pc.set_facecolor(valid[i][2])
            pc.set_alpha(0.65)
        for key in ("cmedians", "cbars", "cmins", "cmaxes"):
            parts[key].set_color("black")
            parts[key].set_linewidth(0.8)

        ax.set_xticks(range(len(valid)))
        ax.set_xticklabels([v[1] for v in valid], fontsize=8)
        ax.set_title(_fmt_feature(feat), fontsize=9)
        ax.grid(axis="y", alpha=0.2)

    for idx in range(len(feat_cols), nrows * ncols):
        row, col = divmod(idx, ncols)
        axes[row][col].set_visible(False)

    plt.tight_layout()
    fpath = out_dir / "distribucion_features_por_label.png"
    plt.savefig(fpath, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"  ✅ {fpath}")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 5 — Evolución temporal de feature_mean coloreado por label (multi-animal)
# ═══════════════════════════════════════════════════════════════════════════════

def plot_temporal_feature_evolution(wins_df: pd.DataFrame, out_dir: Path):
    """
    Para cada feature: una línea por animal, con puntos coloreados por label dominante.
    El eje X es relativo (días desde primer registro) para alinear animales.
    """
    feat_cols = [
        "temperatura_corporal_prom_mean",
        "frec_cardiaca_prom_mean",
        "metros_recorridos_mean",
        "rmssd_mean",
    ]
    feat_cols = [c for c in feat_cols if c in wins_df.columns]
    animals   = sorted(wins_df["animal_id"].unique())

    ncols = 1
    nrows = len(feat_cols)
    fig, axes = plt.subplots(
        nrows, ncols,
        figsize=(16, 3.5 * nrows),
        squeeze=False,
    )
    fig.suptitle(
        "Evolución temporal de features por ventana — comparativa entre vacas\n"
        "(eje X = días desde primer registro de cada animal | puntos coloreados por label)",
        fontsize=12, fontweight="bold",
    )

    for row_i, feat in enumerate(feat_cols):
        ax = axes[row_i][0]

        for animal_id in animals:
            adf = wins_df[wins_df["animal_id"] == animal_id].sort_values("window_center").copy()
            if feat not in adf.columns or adf[feat].isna().all():
                continue

            # Tiempo relativo en días
            t0 = adf["window_center"].min()
            adf["days"] = (adf["window_center"] - t0).dt.total_seconds() / 86400

            # Línea gris de fondo (continuidad)
            ax.plot(adf["days"], adf[feat],
                    color="gray", linewidth=0.7, alpha=0.25, zorder=1)

            # Puntos coloreados por label
            for lbl, grp in adf.groupby("label"):
                ax.scatter(
                    grp["days"], grp[feat],
                    c=label_color(lbl), s=18,
                    alpha=0.75, zorder=2,
                    edgecolors="none",
                )

            # Etiqueta de animal al final
            last = adf.iloc[-1]
            ax.text(
                last["days"] + 0.3, last[feat],
                str(animal_id),
                fontsize=5, color="gray", va="center",
            )

        ax.set_ylabel(_fmt_feature(feat), fontsize=9)
        ax.grid(alpha=0.18)
        ax.set_xlabel("Días desde primer registro", fontsize=8)

        # Leyenda sólo en el primer subplot
        if row_i == 0:
            handles = [
                mpatches.Patch(color=v, label=k)
                for k, v in LABEL_COLORS.items()
            ]
            ax.legend(handles=handles, loc="upper right",
                      fontsize=8, ncol=len(LABEL_COLORS))

    plt.tight_layout()
    fpath = out_dir / "evolucion_temporal_features.png"
    plt.savefig(fpath, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"  ✅ {fpath}")


# ═══════════════════════════════════════════════════════════════════════════════
# PLOT 6 — Resumen estadístico por animal y label
# ═══════════════════════════════════════════════════════════════════════════════

def plot_animal_label_summary(df: pd.DataFrame, wins_df: pd.DataFrame, out_dir: Path):
    """
    Tabla visual: animales en filas, labels en columnas.
    Valor = % de registros raw con ese label.
    Color = intensidad del %.
    """
    animals = sorted(df["animal_id"].unique())
    labels  = sorted(df["label"].dropna().unique())

    matrix = np.zeros((len(animals), len(labels)))
    for i, aid in enumerate(animals):
        sub = df[df["animal_id"] == aid]["label"].value_counts(normalize=True)
        for j, lbl in enumerate(labels):
            matrix[i, j] = sub.get(lbl, 0.0)

    fig, (ax_heat, ax_bar) = plt.subplots(
        1, 2, figsize=(12, max(4, 0.55 * len(animals) + 2)),
        gridspec_kw={"width_ratios": [2, 1]},
    )
    fig.suptitle(
        "Resumen por animal: distribución de labels y cantidad de ventanas generadas",
        fontsize=12, fontweight="bold",
    )

    # Heatmap
    im = ax_heat.imshow(matrix, aspect="auto", cmap="YlOrRd", vmin=0, vmax=1)
    plt.colorbar(im, ax=ax_heat, fraction=0.03, pad=0.03, label="% registros")
    ax_heat.set_xticks(range(len(labels)))
    ax_heat.set_xticklabels(labels, fontsize=9)
    ax_heat.set_yticks(range(len(animals)))
    ax_heat.set_yticklabels([str(a) for a in animals], fontsize=8)
    ax_heat.set_title("% tiempo por label (registros raw)", fontsize=9)
    for i in range(len(animals)):
        for j in range(len(labels)):
            v = matrix[i, j]
            if v > 0.01:
                ax_heat.text(j, i, f"{v:.0%}",
                             ha="center", va="center",
                             fontsize=7,
                             color="white" if v > 0.55 else "black")

    # Barras: n° ventanas por animal
    n_wins = wins_df.groupby("animal_id").size().reindex(animals, fill_value=0)
    bar_colors = ["#3498db"] * len(animals)
    ax_bar.barh(range(len(animals)), n_wins.values, color=bar_colors, alpha=0.78)
    ax_bar.set_yticks(range(len(animals)))
    ax_bar.set_yticklabels([str(a) for a in animals], fontsize=8)
    ax_bar.set_xlabel("N° ventanas generadas", fontsize=8)
    ax_bar.set_title(f"Ventanas por animal\n(w={WINDOW_SIZE}, step={STEP_SIZE})", fontsize=9)
    ax_bar.grid(axis="x", alpha=0.25)
    for i, v in enumerate(n_wins.values):
        ax_bar.text(v + 0.3, i, str(v), va="center", fontsize=7)

    plt.tight_layout()
    fpath = out_dir / "resumen_animales_labels.png"
    plt.savefig(fpath, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"  ✅ {fpath}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Exploración del pipeline de feature engineering")
    parser.add_argument("--csv",    default=CSV_PATH,   help="Ruta al CSV")
    parser.add_argument("--animal", nargs="*", type=int, help="IDs de animales a graficar (default: todos)")
    parser.add_argument("--out",    default="output_exploration", help="Carpeta de salida")
    parser.add_argument("--max-timeline", type=int, default=6,
                        help="Máximo de vacas con timeline individual (default: 6)")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── Carga de datos ────────────────────────────────────────────────────────
    print(f"\n📂 Cargando {args.csv}...")
    df = pd.read_csv(args.csv, parse_dates=["timestamp"])
    print(f"   {len(df):,} registros | {df['animal_id'].nunique()} animales")
    print(f"   Labels únicos: {sorted(df['label'].dropna().unique())}")
    print(f"   Período: {df['timestamp'].min()} → {df['timestamp'].max()}")

    animals_all = sorted(df["animal_id"].unique())
    animals     = args.animal if args.animal else animals_all

    # ── Construcción de ventanas ──────────────────────────────────────────────
    print(f"\n🔧 Construyendo ventanas (w={WINDOW_SIZE}, step={STEP_SIZE})...")
    wins_df = build_windowed_dataset(df[df["animal_id"].isin(animals)].copy())
    print(f"   → {len(wins_df):,} ventanas | {wins_df.shape[1]} columnas")

    print(f"\n📊 Generando plots en '{out_dir}/'...\n")

    # ── Plot 1: timelines individuales ────────────────────────────────────────
    timeline_animals = animals[: args.max_timeline]
    print(f"1️⃣  Timelines individuales ({len(timeline_animals)} vacas):")
    plot_animal_timelines(df, timeline_animals, out_dir)

    # ── Plot 2: comparativa heatmap entre vacas ───────────────────────────────
    print("\n2️⃣  Comparativa de features entre vacas (heatmap):")
    plot_feature_comparison(wins_df, out_dir)

    # ── Plot 3: pureza de label por ventana ───────────────────────────────────
    print("\n3️⃣  Pureza del label dominante por ventana:")
    plot_label_purity(wins_df, out_dir)

    # ── Plot 4: distribución de features por label ────────────────────────────
    print("\n4️⃣  Distribución de features por clase (violinplots):")
    plot_feature_by_label(wins_df, out_dir)

    # ── Plot 5: evolución temporal multi-animal ───────────────────────────────
    print("\n5️⃣  Evolución temporal de features (multi-animal):")
    plot_temporal_feature_evolution(wins_df, out_dir)

    # ── Plot 6: resumen por animal y label ────────────────────────────────────
    print("\n6️⃣  Resumen por animal y distribución de labels:")
    plot_animal_label_summary(df, wins_df, out_dir)

    # ── Exportar tabla de ventanas ────────────────────────────────────────────
    csv_out = out_dir / "ventanas_features.csv"
    wins_df.to_csv(csv_out, index=False)
    print(f"\n💾 Tabla de ventanas exportada: {csv_out}")
    print(f"\n✅ Listo. Todos los archivos en: {out_dir}/\n")


if __name__ == "__main__":
    main()