"""
DAMP - Distributed Animal Monitoring Platform
Generador de datos sintéticos v2

Esquema: el dispositivo IoT procesa en el edge cada 5 minutos
y sube un registro con el promedio/resumen del intervalo.

Columnas finales:
  label, timestamp, animal_id,
  temperatura_corporal_prom,
  hubo_rumia,
  frec_cardiaca_prom,
  rmssd,
  sdnn,
  hubo_vocalizacion,
  latitud, longitud,
  metros_recorridos,
  velocidad_movimiento_prom

Referencia biológica:
  Hogeveen et al. (2011), Khatun et al. (2017),
  Fogsgaard et al. (2012)
"""

import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

np.random.seed(42)

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────
N_DIAS          = 3          # 3 días de simulación
INTERVALO_MIN   = 5          # resumen cada 5 minutos
N_REGISTROS     = (N_DIAS * 24 * 60) // INTERVALO_MIN   # 864 por animal

RODEO = {
    "sana":       list(range(1, 15)),   # BOV_001 – BOV_014
    "subclinica": list(range(15, 18)),  # BOV_015 – BOV_017
    "clinica":    list(range(18, 21)),  # BOV_018 – BOV_020
}

# ─────────────────────────────────────────────
# PARÁMETROS BIOLÓGICOS POR ESTADO
# ─────────────────────────────────────────────
PARAMS = {
    "sana": {
        "temp_media":        38.6,   "temp_std":        0.30,
        "hr_media":          65.0,   "hr_std":          5.0,
        "rmssd_media":       42.0,   "rmssd_std":       7.0,
        "velocidad_media":   1.8,    "velocidad_std":   0.6,   # km/h pastoreo normal
        "prob_rumia":        0.55,   # ~55% de los intervalos hay rumia
        "prob_vocal":        0.06,   # vocaliza poco
    },
    "subclinica": {
        "temp_media":        39.2,   "temp_std":        0.40,
        "hr_media":          78.0,   "hr_std":          7.0,
        "rmssd_media":       27.0,   "rmssd_std":       6.0,
        "velocidad_media":   1.1,    "velocidad_std":   0.5,
        "prob_rumia":        0.35,   # rumia cae — indicador temprano
        "prob_vocal":        0.18,
    },
    "clinica": {
        "temp_media":        40.4,   "temp_std":        0.50,
        "hr_media":          92.0,   "hr_std":          9.0,
        "rmssd_media":       14.0,   "rmssd_std":       4.0,
        "velocidad_media":   0.4,    "velocidad_std":   0.2,
        "prob_rumia":        0.10,   # casi no rumia
        "prob_vocal":        0.30,
    },
}

# ─────────────────────────────────────────────
# RITMO CIRCADIANO
# Vacas tienen dos picos de actividad: 6-8am y 16-18pm
# ─────────────────────────────────────────────
def factor_circadiano(hora_decimal):
    manana = np.exp(-0.5 * ((hora_decimal - 7.0) / 1.5) ** 2)
    tarde  = np.exp(-0.5 * ((hora_decimal - 17.0) / 1.5) ** 2)
    return 0.55 + 0.45 * (manana + tarde)

# ─────────────────────────────────────────────
# GENERADOR POR ANIMAL
# ─────────────────────────────────────────────
def generar_animal(animal_id, estado):
    p   = PARAMS[estado]
    t0  = datetime(2025, 6, 1, 6, 0, 0)

    # Posición base en la pampa húmeda
    lat0 = -34.6037 + np.random.uniform(-0.08, 0.08)
    lon0 = -60.9265 + np.random.uniform(-0.08, 0.08)
    lat, lon = lat0, lon0

    # Radio máximo de desplazamiento según estado
    radio = {"sana": 0.010, "subclinica": 0.005, "clinica": 0.002}[estado]

    registros = []

    for i in range(N_REGISTROS):
        ts   = t0 + timedelta(minutes=i * INTERVALO_MIN)
        hora = ts.hour + ts.minute / 60.0
        circ = factor_circadiano(hora)

        # ── Temperatura ──────────────────────────────────
        # Deriva suave que representa progresión de la enfermedad
        progresion = i / N_REGISTROS
        temp_media_ajustada = p["temp_media"] + (0.4 * progresion if estado != "sana" else 0)
        # Variación circadiana fisiológica (+0.2°C al atardecer)
        temp_circ = 0.1 * np.sin(2 * np.pi * (hora - 6) / 24)
        temp = round(np.clip(
            np.random.normal(temp_media_ajustada, p["temp_std"]) + temp_circ,
            36.5, 42.5
        ), 2)

        # ── Frecuencia cardíaca ──────────────────────────
        hr = round(np.clip(
            np.random.normal(p["hr_media"], p["hr_std"]),
            40.0, 130.0
        ), 1)

        # ── HRV ─────────────────────────────────────────
        rmssd = round(max(5.0, np.random.normal(p["rmssd_media"], p["rmssd_std"])), 1)
        # SDNN siempre un poco mayor que RMSSD (relación fisiológica)
        sdnn  = round(max(rmssd * 1.05, rmssd * np.random.uniform(1.1, 1.5)), 1)

        # ── Rumia ────────────────────────────────────────
        # Sube con el factor circadiano (rumiación post-pastoreo)
        # El IoT la detecta por el patrón rítmico del acelerómetro + giroscopio
        prob_rumia_ajustada = p["prob_rumia"] * (0.7 + 0.6 * circ)
        hubo_rumia = int(np.random.random() < min(prob_rumia_ajustada, 1.0))

        # ── Vocalización ─────────────────────────────────
        hubo_vocalizacion = int(np.random.random() < p["prob_vocal"])

        # ── Movimiento / GPS ─────────────────────────────
        velocidad = round(max(0.0,
            np.random.normal(p["velocidad_media"] * circ, p["velocidad_std"])
        ), 2)   # km/h

        # metros recorridos en el intervalo de 5 minutos
        metros = round(velocidad * (INTERVALO_MIN / 60) * 1000, 1)

        # Random walk GPS proporcional al movimiento
        paso = (velocidad / 3600) * INTERVALO_MIN * 60 / 111320  # grados
        lat += np.random.normal(0, paso * 0.5)
        lon += np.random.normal(0, paso * 0.5)
        lat = float(np.clip(lat, lat0 - radio, lat0 + radio))
        lon = float(np.clip(lon, lon0 - radio, lon0 + radio))

        registros.append({
            "label":                      estado,
            "timestamp":                  ts.strftime("%Y-%m-%d %H:%M:%S"),
            "animal_id":                  f"BOV_{animal_id:03d}",
            "temperatura_corporal_prom":  temp,
            "hubo_rumia":                 hubo_rumia,
            "frec_cardiaca_prom":         hr,
            "rmssd":                      rmssd,
            "sdnn":                       sdnn,
            "hubo_vocalizacion":          hubo_vocalizacion,
            "latitud":                    round(lat, 6),
            "longitud":                   round(lon, 6),
            "metros_recorridos":          metros,
            "velocidad_movimiento_prom":  velocidad,
        })

    return registros

# ─────────────────────────────────────────────
# GENERAR EL DATASET COMPLETO
# ─────────────────────────────────────────────
print("DAMP — Generando dataset v2")
print(f"  {N_DIAS} días · intervalo {INTERVALO_MIN} min · {N_REGISTROS} registros/animal")
print()

todos = []
for estado, ids in RODEO.items():
    for aid in ids:
        filas = generar_animal(aid, estado)
        todos.extend(filas)
        print(f"  ✓ BOV_{aid:03d}  [{estado:>10}]  {len(filas)} registros")

df = pd.DataFrame(todos)

# ─────────────────────────────────────────────
# VALIDACIÓN
# ─────────────────────────────────────────────
print(f"\nShape: {df.shape[0]:,} filas × {df.shape[1]} columnas")
print(f"Columnas: {list(df.columns)}\n")

print("── Promedios por estado ─────────────────────────────")
cols_check = [
    "temperatura_corporal_prom", "frec_cardiaca_prom",
    "rmssd", "sdnn", "metros_recorridos", "velocidad_movimiento_prom"
]
resumen = df.groupby("label")[cols_check].mean().round(2)
print(resumen.to_string())

print("\n── Proporciones binarias ────────────────────────────")
for col in ["hubo_rumia", "hubo_vocalizacion"]:
    prop = df.groupby("label")[col].mean().mul(100).round(1)
    print(f"\n{col} (% de intervalos):")
    print(prop.to_string())

# ─────────────────────────────────────────────
# GUARDAR
# ─────────────────────────────────────────────
output_dir = Path(__file__).resolve().parent
df.to_csv(output_dir / "damp_data.csv", index=False)
df.sample(100, random_state=42).sort_values("timestamp").to_csv(
    output_dir / "damp_sample.csv", index=False
)
print("\n✓ damp_data.csv guardado")
print("✓ damp_sample.csv guardado (100 filas)")
