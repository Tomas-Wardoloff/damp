"""
DAMP - Distributed Animal Monitoring Platform
Generador de datos sintéticos con anomalías realistas

Genera tres archivos en ./data/:
  damp_data_temporal.csv  — dataset completo (todos los animales)
  damp_sample_temporal.csv — muestra de 200 filas
  damp_data_test.csv      — BOV_018 sola (progresión completa para testeo)

Anomalías integradas directamente en el loop:
  - Falla de sensor (NaN esporádico)
  - Spike de temperatura por estrés ambiental en animal sano
  - Caída de HR por artefacto del sensor
  - Rumia falsa positiva por movimiento brusco
  - Animal sano con RMSSD bajo por estrés (confunde al modelo)
  - Subclinica con remisión parcial (baja la fiebre un rato)
  - GPS congelado (misma posición varios registros seguidos)
  - Vocalización en cluster (varias seguidas, no aisladas)

Referencias:
  Khatun et al. (2017), Fogsgaard et al. (2012),
  Hogeveen et al. (2011), Radostits et al. (2007)
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

np.random.seed(42)

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
N_DIAS = 30
IVMIN  = 5
NR     = (N_DIAS * 24 * 60) // IVMIN   # 864 registros/animal

RODEO = {
    "sana":       {"ids": list(range(1, 15)),  "infectados": False},
    "subclinica": {"ids": list(range(15, 18)), "infectados": True, "inicio": 100, "max_prog": 0.55},
    "clinica":    {"ids": list(range(18, 21)), "infectados": True, "inicio": 24,  "max_prog": 1.0},
}

BASE = {
    "temp": 38.6,  "temp_s": 0.45,
    "hr":   65.0,  "hr_s":   11.0,
    "rmssd":40.0,  "rmssd_s":9.0,
    "vel":   1.7,  "vel_s":  0.70,
    "p_rumia": 0.52,
    "p_vocal": 0.07,
}

DELTA = {
    "temp":    +1.8,
    "hr":      +12.0,
    "rmssd":   -26.0,
    "vel":      -1.3,
    "p_rumia": -0.42,
    "p_vocal": +0.22,
}

# ─────────────────────────────────────────────
# HELPERS INLINE
# ─────────────────────────────────────────────
def sigmoide(i, inicio):
    h = (i - inicio) * IVMIN / 60.0
    return 0.0 if h <= 0 else float(1 / (1 + np.exp(-0.2 * (h - 24))))

def fase(p):
    return "sana" if p < 0.15 else ("subclinica" if p < 0.60 else "clinica")

def circ(h):
    return 0.55 + 0.45 * (np.exp(-0.5*((h-7)/1.5)**2) + np.exp(-0.5*((h-17)/1.5)**2))

# ─────────────────────────────────────────────
# LOOP PRINCIPAL
# ─────────────────────────────────────────────
todos = []

for estado, cfg in RODEO.items():
    for aid in cfg["ids"]:

        # posición GPS base
        lat0 = -34.6037 + np.random.uniform(-0.08, 0.08)
        lon0 = -60.9265 + np.random.uniform(-0.08, 0.08)
        lat, lon = lat0, lon0
        radio = 0.010 if estado == "sana" else 0.006

        # inicio de infección con variabilidad individual
        if cfg["infectados"]:
            inicio_inf = cfg["inicio"] + np.random.randint(-20, 20)
        else:
            inicio_inf = NR + 1

        t0 = datetime(2025, 6, 1, 6, 0, 0)

        # ── flags de anomalías persistentes por animal ────
        # GPS congelado: algunos animales tienen períodos donde el GPS no actualiza
        gps_freeze_start = np.random.randint(200, 600) if np.random.random() < 0.3 else -1
        gps_freeze_len   = np.random.randint(8, 20)   # 40-100 min congelado

        # Estrés ambiental: ola de calor en el día 2 afecta a algunos sanos
        tiene_estres_termico = (estado == "sana") and (np.random.random() < 0.25)
        estres_inicio = np.random.randint(260, 320) if tiene_estres_termico else -1
        estres_len    = np.random.randint(20, 50)

        # Remisión parcial en subclinica (fiebre baja un rato, luego vuelve)
        tiene_remision = (estado == "subclinica") and (np.random.random() < 0.4)
        remision_inicio = np.random.randint(350, 500) if tiene_remision else -1
        remision_len    = np.random.randint(15, 35)

        # Animal sano con RMSSD crónicamente bajo (estrés social, dominancia)
        rmssd_bajo_cronico = (estado == "sana") and (np.random.random() < 0.15)

        # Cluster de vocalización (vocaliza en ráfagas, no random)
        vocal_cluster_start = np.random.randint(100, 700) if np.random.random() < 0.35 else -1
        vocal_cluster_len   = np.random.randint(4, 10)

        print(f"  ✓ BOV_{aid:03d}  [{estado:>10}]", end="")
        anomalias = []
        if gps_freeze_start > 0:       anomalias.append("gps_freeze")
        if tiene_estres_termico:        anomalias.append("estres_termico")
        if tiene_remision:              anomalias.append("remision_parcial")
        if rmssd_bajo_cronico:          anomalias.append("rmssd_bajo")
        if vocal_cluster_start > 0:     anomalias.append("vocal_cluster")
        print(f"  {'  '.join(anomalias) if anomalias else ''}")

        for i in range(NR):
            ts = t0 + timedelta(minutes=i * IVMIN)
            h  = ts.hour + ts.minute / 60.0
            c  = circ(h)
            rc = np.random.normal(0, 1)  # ruido correlacionado entre sensores

            # ── Progresión de la enfermedad ───────────────
            prog = min(sigmoide(i, inicio_inf), cfg.get("max_prog", 1.0))

            # Aplicar remisión parcial: la progresión baja temporalmente
            if tiene_remision and remision_inicio <= i < remision_inicio + remision_len:
                factor_remision = 0.5 + 0.5 * abs(
                    np.sin(np.pi * (i - remision_inicio) / remision_len)
                )
                prog = prog * factor_remision

            label_i = fase(prog)

            # Interpolar valores según progresión
            temp_m  = BASE["temp"]    + prog * DELTA["temp"]
            hr_m    = BASE["hr"]      + prog * DELTA["hr"]
            rmssd_m = BASE["rmssd"]   + prog * DELTA["rmssd"]
            vel_m   = BASE["vel"]     + prog * DELTA["vel"]
            p_rum   = BASE["p_rumia"] + prog * DELTA["p_rumia"]
            p_voc   = BASE["p_vocal"] + prog * DELTA["p_vocal"]

            # Std crece con la enfermedad
            temp_s  = BASE["temp_s"]  * (1 + 0.4 * prog)
            hr_s    = BASE["hr_s"]    * (1 + 0.5 * prog)
            rmssd_s = BASE["rmssd_s"] * (1 + 0.3 * prog)
            vel_s   = BASE["vel_s"]   * (1 + 0.3 * prog)

            # ── Estrés térmico en sanos (confunde al modelo) ──
            temp_extra = 0.0
            hr_extra   = 0.0
            if tiene_estres_termico and estres_inicio <= i < estres_inicio + estres_len:
                factor_calor = np.sin(np.pi * (i - estres_inicio) / estres_len)
                temp_extra = factor_calor * np.random.uniform(0.5, 1.1)
                hr_extra   = factor_calor * np.random.uniform(4, 9)

            # ── TEMPERATURA ───────────────────────────────
            temp = (
                np.random.normal(temp_m, temp_s)
                + 0.1 * np.sin(2 * np.pi * (h - 6) / 24)
                + rc * 0.08
                + temp_extra
            )
            # Falla de sensor: NaN esporádico (~0.8% de los registros)
            if np.random.random() < 0.008:
                temp = np.nan
            else:
                temp = round(float(np.clip(temp, 36.5, 42.5)), 2)

            # ── FRECUENCIA CARDÍACA ───────────────────────
            hr = (
                np.random.normal(hr_m, hr_s)
                + rc * 1.8
                + hr_extra
            )
            # Artefacto: spike negativo de HR por movimiento brusco (~1%)
            if np.random.random() < 0.010:
                hr = np.random.uniform(38, 48)  # caída brusca — artefacto
            else:
                hr = round(float(np.clip(hr, 38, 130)), 1)

            # ── HRV ──────────────────────────────────────
            rmssd_base = max(5.0, rmssd_m)
            # Animal con RMSSD crónicamente bajo por estrés social
            if rmssd_bajo_cronico:
                rmssd_base = max(5.0, rmssd_base - np.random.uniform(8, 14))
            rmssd = round(float(max(4.0,
                np.random.normal(rmssd_base, rmssd_s) - rc * 1.0
            )), 1)
            sdnn = round(float(max(rmssd * 1.05, rmssd * np.random.uniform(1.1, 1.45))), 1)

            # ── RUMIA ─────────────────────────────────────
            prob_rum = min(max(0, p_rum) * (0.7 + 0.6 * c), 1.0)
            # Falso positivo de rumia: movimiento brusco confunde al acelerómetro (~2%)
            if np.random.random() < 0.020:
                prob_rum = min(prob_rum + 0.6, 1.0)
            hubo_rumia = int(np.random.random() < prob_rum)

            # ── VOCALIZACIÓN ──────────────────────────────
            prob_voc = p_voc
            # Cluster de vocalización: vocaliza en ráfaga por interacción social
            if vocal_cluster_start > 0 and vocal_cluster_start <= i < vocal_cluster_start + vocal_cluster_len:
                prob_voc = min(prob_voc + 0.65, 1.0)
            hubo_vocal = int(np.random.random() < prob_voc)

            # ── VELOCIDAD / GPS ───────────────────────────
            vel = round(float(max(0.0,
                np.random.normal(max(0.0, vel_m) * c, vel_s)
            )), 2)
            metros = round(vel * (IVMIN / 60) * 1000, 1)

            # GPS congelado: misma posición durante N registros
            if gps_freeze_start > 0 and gps_freeze_start <= i < gps_freeze_start + gps_freeze_len:
                # no actualiza lat/lon
                pass
            else:
                paso = (vel / 3600) * IVMIN * 60 / 111320
                lat = float(np.clip(lat + np.random.normal(0, paso * 0.5), lat0 - radio, lat0 + radio))
                lon = float(np.clip(lon + np.random.normal(0, paso * 0.5), lon0 - radio, lon0 + radio))

            todos.append({
                "label":                      label_i,
                "label_animal":               estado,
                "timestamp":                  ts.strftime("%Y-%m-%d %H:%M:%S"),
                "animal_id":                  f"BOV_{aid:03d}",
                "progresion":                 round(prog, 4),
                "temperatura_corporal_prom":  temp,
                "hubo_rumia":                 hubo_rumia,
                "frec_cardiaca_prom":         hr,
                "rmssd":                      rmssd,
                "sdnn":                       sdnn,
                "hubo_vocalizacion":          hubo_vocal,
                "latitud":                    round(lat, 6),
                "longitud":                   round(lon, 6),
                "metros_recorridos":          metros,
                "velocidad_movimiento_prom":  vel,
            })

# ─────────────────────────────────────────────
# DATAFRAME Y VALIDACIÓN
# ─────────────────────────────────────────────
df = pd.DataFrame(todos)

print(f"\nShape: {df.shape[0]:,} filas × {df.shape[1]} columnas")
print(f"NaNs por columna:\n{df.isnull().sum()[df.isnull().sum() > 0].to_string()}")

print("\n── Distribución de labels ────────────────────────────")
print(df.groupby(["label_animal", "label"]).size().to_string())

print("\n── Promedios por label (con NaNs ignorados) ──────────")
cols = ["temperatura_corporal_prom", "frec_cardiaca_prom", "rmssd", "metros_recorridos"]
print(df.groupby("label")[cols].mean().round(2).to_string())

print("\n── Progresión BOV_018 — cada 2 horas ────────────────")
b18 = df[df.animal_id == "BOV_018"][
    ["timestamp","progresion","label","temperatura_corporal_prom","frec_cardiaca_prom","rmssd"]
]
print(b18.iloc[::24].head(20).to_string(index=False))

# ─────────────────────────────────────────────
# GUARDAR
# ─────────────────────────────────────────────
out = Path(__file__).resolve().parent / "data"
out.mkdir(parents=True, exist_ok=True)

# Dataset completo
df.to_csv(out / "damp_data_temporal.csv", index=False)

# Sample 200 filas
df.sample(200, random_state=42).sort_values("timestamp").to_csv(
    out / "damp_sample_temporal.csv", index=False
)

# Test: BOV_018 regenerada de cero (no filtrada del dataset)
# Re-generamos solo esa vaca con el mismo seed para consistencia
np.random.seed(22)
cfg_test = {"infectados": True, "inicio": 24, "max_prog": 1.0}
lat0t = -34.6037 + np.random.uniform(-0.08, 0.08)
lon0t = -60.9265 + np.random.uniform(-0.08, 0.08)
lat_t, lon_t = lat0t, lon0t
inicio_t = cfg_test["inicio"] + np.random.randint(-20, 20)
t0t = datetime(2025, 6, 1, 6, 0, 0)
gps_ft = np.random.randint(200, 400)
gps_fl = np.random.randint(8, 18)
test_rows = []

for i in range(NR):
    ts = t0t + timedelta(minutes=i * IVMIN)
    h  = ts.hour + ts.minute / 60.0
    c  = circ(h)
    rc = np.random.normal(0, 1)
    prog = min(sigmoide(i, inicio_t), 1.0)
    label_i = fase(prog)

    temp_m  = BASE["temp"]    + prog * DELTA["temp"]
    hr_m    = BASE["hr"]      + prog * DELTA["hr"]
    rmssd_m = BASE["rmssd"]   + prog * DELTA["rmssd"]
    vel_m   = BASE["vel"]     + prog * DELTA["vel"]
    p_rum   = BASE["p_rumia"] + prog * DELTA["p_rumia"]
    p_voc   = BASE["p_vocal"] + prog * DELTA["p_vocal"]

    temp_s  = BASE["temp_s"]  * (1 + 0.4 * prog)
    hr_s    = BASE["hr_s"]    * (1 + 0.5 * prog)
    rmssd_s = BASE["rmssd_s"] * (1 + 0.3 * prog)
    vel_s   = BASE["vel_s"]   * (1 + 0.3 * prog)

    temp = np.random.normal(temp_m, temp_s) + 0.1*np.sin(2*np.pi*(h-6)/24) + rc*0.08
    if np.random.random() < 0.008:
        temp = np.nan
    else:
        temp = round(float(np.clip(temp, 36.5, 42.5)), 2)

    hr = np.random.normal(hr_m, hr_s) + rc * 1.8
    if np.random.random() < 0.010:
        hr = round(float(np.random.uniform(38, 48)), 1)
    else:
        hr = round(float(np.clip(hr, 38, 130)), 1)

    rmssd = round(float(max(4.0, np.random.normal(max(5.0,rmssd_m), rmssd_s) - rc*1.0)), 1)
    sdnn  = round(float(max(rmssd*1.05, rmssd*np.random.uniform(1.1,1.45))), 1)

    prob_rum = min(max(0, p_rum) * (0.7 + 0.6*c), 1.0)
    if np.random.random() < 0.020: prob_rum = min(prob_rum + 0.6, 1.0)
    hubo_rumia = int(np.random.random() < prob_rum)
    hubo_vocal = int(np.random.random() < p_voc)

    vel = round(float(max(0.0, np.random.normal(max(0.0,vel_m)*c, vel_s))), 2)
    metros = round(vel * (IVMIN/60) * 1000, 1)

    if gps_ft <= i < gps_ft + gps_fl:
        pass
    else:
        paso = (vel/3600)*IVMIN*60/111320
        lat_t = float(np.clip(lat_t + np.random.normal(0, paso*0.5), lat0t-0.006, lat0t+0.006))
        lon_t = float(np.clip(lon_t + np.random.normal(0, paso*0.5), lon0t-0.006, lon0t+0.006))

    test_rows.append({
        "label": label_i, "label_animal": "clinica",
        "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "animal_id": "BOV_018", "progresion": round(prog, 4),
        "temperatura_corporal_prom": temp, "hubo_rumia": hubo_rumia,
        "frec_cardiaca_prom": hr, "rmssd": rmssd, "sdnn": sdnn,
        "hubo_vocalizacion": hubo_vocal,
        "latitud": round(lat_t, 6), "longitud": round(lon_t, 6),
        "metros_recorridos": metros, "velocidad_movimiento_prom": vel,
    })

df_test = pd.DataFrame(test_rows)
df_test.to_csv(out / "damp_data_test.csv", index=False)

print(f"\n✓ damp_data_temporal.csv  → {len(df):,} filas")
print(f"✓ damp_sample_temporal.csv → 200 filas")
print(f"✓ damp_data_test.csv       → {len(df_test)} filas (BOV_018 regenerada)")
print(f"  labels test: {df_test['label'].value_counts().to_dict()}")
print(f"  NaNs en test: {df_test.isnull().sum().sum()}")
print(f"\nTodo guardado en: {out}")