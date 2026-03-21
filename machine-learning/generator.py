"""
DAMP - Generador de datos sintéticos para entrenamiento
5 clases: sana | mastitis | celo | febril | digestivo

Diferencias vs life_stories:
  - Más drift temporal (el modelo necesita ver tendencias claras)
  - Más animales por clase para balance
  - Progresión sigmoide realista por clase
  - Anomalías integradas para robustez
"""

import math
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

np.random.seed(42)

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
N_DIAS = 20
IVMIN  = 5
NR     = (N_DIAS * 24 * 60) // IVMIN

# IDs por clase — 10 animales por clase = 60 total
RODEO = {
    "sana":       {"ids": list(range(1,  11)), "tipo": "sana"},
    "mastitis":   {"ids": list(range(11, 21)), "tipo": "progresiva"},
    "celo":       {"ids": list(range(21, 31)), "tipo": "celo"},
    "febril":     {"ids": list(range(31, 41)), "tipo": "progresiva"},
    "digestivo":  {"ids": list(range(41, 51)), "tipo": "progresiva"},
}

# ─────────────────────────────────────────────
# PARÁMETROS BASE — animal sano
# ─────────────────────────────────────────────
BASE = {
    "temp":    38.6, "temp_s":   0.55,
    "hr":      65.0, "hr_s":    11.0,
    "rmssd":   40.0, "rmssd_s": 13.0,
    "vel":      1.7, "vel_s":    1.00,
    "p_rumia": 0.52,
    "p_vocal": 0.07,
}

# ─────────────────────────────────────────────
# DELTAS POR CLASE — cuánto cambia cada feature al llegar a prog=1.0
# El drift hace que el modelo aprenda tendencias, no solo valores absolutos
# ─────────────────────────────────────────────
DELTAS = {
    "sana": {
        "temp": 0.0, "hr": 0.0, "rmssd": 0.0,
        "vel": 0.0, "p_rumia": 0.0, "p_vocal": 0.0,
        "max_prog": 0.0,
    },
    "mastitis": {
        # Temp alta, RMSSD muy bajo, movimiento muy bajo, rumia casi cero
        "temp": +1.8, "hr": +24.0, "rmssd": -26.0,
        "vel": -1.10, "p_rumia": -0.42, "p_vocal": +0.20,
        "max_prog": 1.0,
    },
    "celo": {
        # Temp casi normal, HR sube leve, movimiento x3, rumia ok, vocal alta
        # El celo es diferente: no es patológico, el movimiento es el feature clave
        "temp": +0.2, "hr": +9.0, "rmssd": -4.0,
        "vel": +2.8,  "p_rumia": -0.05, "p_vocal": +0.22,
        "max_prog": 1.0,
    },
    "febril": {
        # Temp alta IGUAL que mastitis, PERO movimiento casi normal y RMSSD ok
        # Eso es lo que distingue febril de mastitis
        "temp": +1.7, "hr": +14.0, "rmssd": -8.0,
        "vel": -0.25, "p_rumia": -0.15, "p_vocal": +0.10,
        "max_prog": 1.0,
    },
    "digestivo": {
        # Rumia colapsa primero (feature clave), temp leve, movimiento bajo
        # La rumia es el indicador más temprano y discriminante
        "temp": +0.8, "hr": +16.0, "rmssd": -14.0,
        "vel": -0.90, "p_rumia": -0.44, "p_vocal": +0.22,
        "max_prog": 1.0,
    },
}

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def sigmoide(i, inicio, pendiente=0.2, centro=24):
    h = (i - inicio) * IVMIN / 60.0
    return 0.0 if h <= 0 else float(1 / (1 + np.exp(-pendiente * (h - centro))))

def circ(h):
    """Factor de actividad circadiana (0-1). Picos: 7am y 17pm. Mínimo: 2-4am."""
    return 0.55 + 0.45 * (np.exp(-0.5*((h-7)/1.5)**2) + np.exp(-0.5*((h-17)/1.5)**2))

def es_noche(h):
    """True si es horario nocturno de descanso (21hs-5hs)."""
    return h >= 21 or h < 5

def factor_nocturno(h):
    """
    Factor 0-1 de profundidad del descanso nocturno.
    1.0 = noche profunda (2-3am), 0.0 = plena actividad diurna.
    Las vacas tienen descanso profundo entre 0-4am.
    """
    # Gaussiana centrada en las 2am
    d = min(abs(h - 2), abs(h - 2 + 24), abs(h - 2 - 24))
    return float(np.exp(-0.5 * (d / 2.5) ** 2))

def fase_from_prog(prog, clase):
    """Determina el label del registro según la progresión y la clase."""
    if clase == "sana":
        return "sana"
    if clase == "mastitis":
        return "mastitis" if prog >= 0.15 else "sana"
    if clase == "celo":
        return "celo" if prog >= 0.15 else "sana"
    if clase == "febril":
        return "febril" if prog >= 0.12 else "sana"
    if clase == "digestivo":
        return "digestivo" if prog >= 0.12 else "sana"
    return clase

# ─────────────────────────────────────────────
# INICIO DE PROGRESIÓN POR CLASE
# Cuándo arranca la condición (en tick)
# ─────────────────────────────────────────────
INICIO_BASE = {
    "sana":       NR + 1,   # nunca
    "mastitis":   100,
    "celo":       120,
    "febril":     300,      # arranca tarde — más ventanas ambiguas para entrenar
    "digestivo":  90,
}

# ─────────────────────────────────────────────
# LOOP PRINCIPAL
# ─────────────────────────────────────────────
todos = []

for clase, cfg in RODEO.items():
    d = DELTAS[clase]

    for aid in cfg["ids"]:
        lat0 = -34.6037 + np.random.uniform(-0.08, 0.08)
        lon0 = -60.9265 + np.random.uniform(-0.08, 0.08)
        lat, lon = lat0, lon0
        radio = 0.018 if clase == "celo" else (0.010 if clase == "sana" else 0.007)

        inicio_inf = INICIO_BASE[clase] + np.random.randint(-30, 30)
        if clase == "sana":
            inicio_inf = NR + 1

        t0 = datetime(2025, 6, 1, 6, 0, 0)

        # Anomalías por animal
        gps_freeze_start    = np.random.randint(200, NR-100) if np.random.random() < 0.25 else -1
        gps_freeze_len      = np.random.randint(8, 20)
        tiene_estres        = (clase == "sana") and (np.random.random() < 0.20)
        estres_inicio       = np.random.randint(200, 400) if tiene_estres else -1
        estres_len          = np.random.randint(20, 60)
        rmssd_bajo_cronico  = (clase == "sana") and (np.random.random() < 0.12)
        vocal_cluster_start = np.random.randint(50, NR-50) if np.random.random() < 0.30 else -1
        vocal_cluster_len   = np.random.randint(4, 12)
        tiene_remision      = False
        remision_inicio     = -1
        remision_len        = 0

        anomalias = []
        if gps_freeze_start > 0:    anomalias.append("gps_freeze")
        if tiene_estres:             anomalias.append("estres")
        if rmssd_bajo_cronico:       anomalias.append("rmssd_bajo")
        if vocal_cluster_start > 0:  anomalias.append("vocal_cluster")
        if tiene_remision:           anomalias.append("remision")
        tag = "  " + "  ".join(anomalias) if anomalias else ""
        print(f"  ✓ BOV_{aid:03d}  [{clase:>10}]{tag}")

        for i in range(NR):
            ts = t0 + timedelta(minutes=i * IVMIN)
            h  = ts.hour + ts.minute / 60.0
            c  = circ(h)
            rc = np.random.normal(0, 1)

            # Progresión
            prog = min(sigmoide(i, inicio_inf), d["max_prog"])

            if tiene_remision and remision_inicio <= i < remision_inicio + remision_len:
                factor = 0.5 + 0.5 * abs(np.sin(np.pi * (i - remision_inicio) / remision_len))
                prog = prog * factor

            label_i = fase_from_prog(prog, clase)

            # Valores interpolados
            temp_m  = BASE["temp"]    + prog * d["temp"]
            hr_m    = BASE["hr"]      + prog * d["hr"]
            rmssd_m = BASE["rmssd"]   + prog * d["rmssd"]
            vel_m   = BASE["vel"]     + prog * d["vel"]
            p_rum   = BASE["p_rumia"] + prog * d["p_rumia"]
            p_voc   = BASE["p_vocal"] + prog * d["p_vocal"]

            # Std crece con la enfermedad
            temp_s  = BASE["temp_s"]  * (1 + 0.4 * prog)
            hr_s    = BASE["hr_s"]    * (1 + 0.5 * prog)
            rmssd_s = BASE["rmssd_s"] * (1 + 0.3 * prog)
            vel_s   = BASE["vel_s"]   * (1 + 0.3 * prog)

            # Estrés térmico en sanos
            temp_extra = hr_extra = 0.0
            if tiene_estres and estres_inicio <= i < estres_inicio + estres_len:
                f = np.sin(np.pi * (i - estres_inicio) / estres_len)
                temp_extra = f * np.random.uniform(0.4, 0.9)
                hr_extra   = f * np.random.uniform(3, 8)

            # Celo: movimiento nocturno amplificado
            if clase == "celo" and prog > 0.1:
                hora_celo = (math.exp(-0.5 * ((h - 23) / 3.0) ** 2) +
                             math.exp(-0.5 * ((h - 1)  / 2.5) ** 2)
                             if True else 0)
                hora_celo = math.exp(-0.5 * ((h - 23) / 3.0) ** 2) + \
                            math.exp(-0.5 * ((h - 1)  / 2.5) ** 2)
                vel_m = vel_m + hora_celo * prog * 1.8

            # ── Factores circadianos ──────────────────────────
            fn = factor_nocturno(h)   # 0=día, 1=noche profunda

            # Temperatura — baja 0.25°C en noche profunda
            temp_circ = 0.1 * np.sin(2*np.pi*(h-6)/24) - fn * 0.25
            temp = np.random.normal(temp_m, temp_s) + temp_circ + rc*0.08 + temp_extra
            temp = np.nan if np.random.random() < 0.008 else round(float(np.clip(temp, 36.5, 42.5)), 2)

            # HR — baja 6-8 bpm de noche (sistema parasimpático domina)
            hr_circ = -fn * 7.0
            hr = np.random.normal(hr_m + hr_circ, hr_s) + rc * 1.8 + hr_extra
            hr = round(float(np.random.uniform(38, 48)), 1) if np.random.random() < 0.010 \
                 else round(float(np.clip(hr, 38, 130)), 1)

            # HRV — RMSSD sube de noche (descanso = más variabilidad cardíaca)
            rmssd_base = max(5.0, rmssd_m + fn * 8.0)
            if rmssd_bajo_cronico:
                rmssd_base = max(5.0, rmssd_base - np.random.uniform(7, 13))
            rmssd = round(float(max(4.0, np.random.normal(rmssd_base, rmssd_s) - rc * 1.0)), 1)
            sdnn  = round(float(max(rmssd * 1.05, rmssd * np.random.uniform(1.1, 1.45))), 1)

            # Rumia — mayor de noche (60-70% ocurre echada en descanso nocturno)
            # Modulada por: estado del animal + hora del día
            rum_noche = 1.0 + fn * 0.6   # hasta +60% de probabilidad de noche
            prob_rum = min(max(0, p_rum) * (0.5 + 0.5 * c + fn * 0.5) * rum_noche, 1.0)
            if np.random.random() < 0.018:
                prob_rum = min(prob_rum + 0.55, 1.0)
            hubo_rumia = int(np.random.random() < prob_rum)

            # Vocalización
            prob_voc = p_voc
            if vocal_cluster_start > 0 and vocal_cluster_start <= i < vocal_cluster_start + vocal_cluster_len:
                prob_voc = min(prob_voc + 0.60, 1.0)
            hubo_vocal = int(np.random.random() < prob_voc)

            # Velocidad — de noche casi cero (animales echados o muy quietos)
            # El factor nocturno reduce la velocidad base, el circadiano la modula de día
            vel_noche = max(0.0, vel_m * c * (1 - fn * 0.85))   # noche: ~15% de la vel diurna
            vel = round(float(max(0.0, np.random.normal(vel_noche, vel_s * (1 - fn*0.5)))), 2)
            metros = round(vel * (IVMIN / 60) * 1000, 1)

            if gps_freeze_start > 0 and gps_freeze_start <= i < gps_freeze_start + gps_freeze_len:
                pass
            else:
                paso = (vel / 3600) * IVMIN * 60 / 111320
                lat = float(np.clip(lat + np.random.normal(0, paso * 0.5), lat0 - radio, lat0 + radio))
                lon = float(np.clip(lon + np.random.normal(0, paso * 0.5), lon0 - radio, lon0 + radio))

            todos.append({
                "label":                      label_i,
                "label_animal":               clase,
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
print(f"NaNs: {df.isnull().sum()[df.isnull().sum()>0].to_string()}")

print("\n── Distribución de labels ────────────────────────────")
print(df.groupby(["label_animal","label"]).size().to_string())

print("\n── Promedios por label ───────────────────────────────")
cols = ["temperatura_corporal_prom","frec_cardiaca_prom","rmssd","metros_recorridos"]
print(df.groupby("label")[cols].mean().round(2).to_string())

# ─────────────────────────────────────────────
# GUARDAR
# ─────────────────────────────────────────────
out = Path(__file__).resolve().parent / "data"
out.mkdir(parents=True, exist_ok=True)

df.to_csv(out / "damp_data_temporal.csv", index=False)
df.sample(200, random_state=42).sort_values("timestamp").to_csv(out / "damp_sample_temporal.csv", index=False)

print(f"\n✓ damp_data_temporal.csv   → {len(df):,} filas")
print(f"✓ damp_sample_temporal.csv → 200 filas")
print(f"\nTodo guardado en: {out}")