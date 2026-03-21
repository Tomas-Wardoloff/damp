"""
DAMP - Distributed Animal Monitoring Platform
Generador de datos sintéticos — versión final con progresión temporal

Biología implementada (Khatun 2017, Fogsgaard 2012):
  Hora 0:     bacteria ingresa al cuarto
  Hora 0-12:  fase subclínica silenciosa — temp sube apenas
  Hora 12-24: fase subclínica manifiesta — temp +0.8C, rumia cae
  Hora 24-48: fase clínica — fiebre clara, animal comprometido

Columnas generadas:
  label               — fase en ese registro (sana/subclinica/clinica)
  label_animal        — clase final del animal
  timestamp
  animal_id
  progresion          — factor 0-1 de avance de la enfermedad
  temperatura_corporal_prom
  hubo_rumia
  frec_cardiaca_prom
  rmssd
  sdnn
  hubo_vocalizacion
  latitud / longitud
  metros_recorridos
  velocidad_movimiento_prom

Uso:
  python damp_generator_final.py
  → genera damp_data_temporal.csv en la misma carpeta
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

np.random.seed(42)

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────
N_DIAS      = 3
IVMIN       = 5       # intervalo en minutos
NR          = (N_DIAS * 24 * 60) // IVMIN   # 864 registros por animal

RODEO = {
    # 14 sanas: sin infección, solo ruido fisiológico normal
    "sana":       {"ids": list(range(1, 15)),  "infectados": False},
    # 3 subclínicas: se infectan en el día 1 — progresan hasta fase subclinica
    "subclinica": {"ids": list(range(15, 18)), "infectados": True, "inicio": 100, "max_prog": 0.55},
    # 3 clínicas: se infectan en el día 0 — progresan a clínica plena
    "clinica":    {"ids": list(range(18, 21)), "infectados": True, "inicio": 24,  "max_prog": 1.0},
}

# ─────────────────────────────────────────────
# PARÁMETROS BASE — animal completamente sano
# Referencia: Radostits et al. (2007), Khatun et al. (2017)
# ─────────────────────────────────────────────
BASE = {
    "temp":     38.6,  "temp_s":    0.45,
    "hr":       65.0,  "hr_s":      7.0,
    "rmssd":    40.0,  "rmssd_s":   9.0,
    "vel":       1.7,  "vel_s":     0.70,
    "p_rumia":  0.52,
    "p_vocal":  0.07,
}

# Delta máximo al llegar a mastitis clínica plena
# Referencia: Fogsgaard et al. (2012), Hogeveen et al. (2011)
DELTA_CLINICA = {
    "temp":    +1.8,    # fiebre: +1.8°C
    "hr":      +26.0,   # taquicardia: +26 bpm
    "rmssd":   -26.0,   # HRV cae: -26 ms
    "vel":      -1.3,   # movimiento cae: -1.3 km/h
    "p_rumia": -0.42,   # rumia cae de 0.52 a 0.10
    "p_vocal": +0.22,   # vocalización sube de 0.07 a 0.29
}

# ─────────────────────────────────────────────
# FUNCIÓN DE PROGRESIÓN — curva sigmoide
# Simula la naturaleza gradual de la mastitis:
# lenta al inicio, rápida en el punto de inflexión (24hs),
# se estabiliza al llegar a estado clínico
# ─────────────────────────────────────────────
def progresion_mastitis(i, hora_inicio_infeccion):
    horas = (i - hora_inicio_infeccion) * IVMIN / 60.0
    if horas <= 0:
        return 0.0
    return float(1 / (1 + np.exp(-0.2 * (horas - 24))))

def fase(prog):
    if prog < 0.15:
        return "sana"
    if prog < 0.60:
        return "subclinica"
    return "clinica"

# ─────────────────────────────────────────────
# RITMO CIRCADIANO
# Dos picos de actividad: 6-8am y 16-18pm
# ─────────────────────────────────────────────
def factor_circadiano(hora):
    m = np.exp(-0.5 * ((hora - 7.0) / 1.5) ** 2)
    t = np.exp(-0.5 * ((hora - 17.0) / 1.5) ** 2)
    return 0.55 + 0.45 * (m + t)

# ─────────────────────────────────────────────
# EVENTOS PUNTUALES (2.5% de los registros)
# Simulan sustos, calor extremo, interacciones sociales
# ─────────────────────────────────────────────
def hay_evento(i, animal_id):
    state = np.random.get_state()
    np.random.seed(animal_id * 1000 + i)
    resultado = np.random.random() < 0.025
    np.random.set_state(state)
    return resultado

# ─────────────────────────────────────────────
# GENERADOR POR ANIMAL
# ─────────────────────────────────────────────
def generar_animal(aid, estado, cfg):
    lat0 = -34.6037 + np.random.uniform(-0.08, 0.08)
    lon0 = -60.9265 + np.random.uniform(-0.08, 0.08)
    lat, lon = lat0, lon0
    radio = 0.010 if estado == "sana" else 0.006

    # Inicio de infección con variabilidad entre animales
    if cfg["infectados"]:
        inicio_inf = cfg["inicio"] + np.random.randint(-20, 20)
    else:
        inicio_inf = NR + 1   # nunca se infecta

    t0 = datetime(2025, 6, 1, 6, 0, 0)
    rows = []

    for i in range(NR):
        ts  = t0 + timedelta(minutes=i * IVMIN)
        h   = ts.hour + ts.minute / 60.0
        c   = factor_circadiano(h)
        rc  = np.random.normal(0, 1)   # ruido correlacionado entre sensores
        ev  = hay_evento(i, aid)

        # Factor de progresión — el corazón del modelo
        prog = min(
            progresion_mastitis(i, inicio_inf),
            cfg.get("max_prog", 1.0)
        )
        label_i = fase(prog)

        # Valores interpolados entre base y estado clínico según progresión
        temp_m  = BASE["temp"]    + prog * DELTA_CLINICA["temp"]
        hr_m    = BASE["hr"]      + prog * DELTA_CLINICA["hr"]
        rmssd_m = BASE["rmssd"]   + prog * DELTA_CLINICA["rmssd"]
        vel_m   = BASE["vel"]     + prog * DELTA_CLINICA["vel"]
        p_rum   = BASE["p_rumia"] + prog * DELTA_CLINICA["p_rumia"]
        p_voc   = BASE["p_vocal"] + prog * DELTA_CLINICA["p_vocal"]

        # Std aumenta con la enfermedad — más variabilidad fisiológica bajo estrés
        temp_s  = BASE["temp_s"]  * (1 + 0.4 * prog)
        hr_s    = BASE["hr_s"]    * (1 + 0.5 * prog)
        rmssd_s = BASE["rmssd_s"] * (1 + 0.3 * prog)
        vel_s   = BASE["vel_s"]   * (1 + 0.3 * prog)

        # ── Temperatura ──────────────────────────────────
        temp = round(float(np.clip(
            np.random.normal(temp_m, temp_s)
            + 0.1 * np.sin(2 * np.pi * (h - 6) / 24)  # variación circadiana
            + rc * 0.08
            + (np.random.uniform(0.1, 0.4) if ev else 0),
            36.5, 42.5
        )), 2)

        # ── Frecuencia cardíaca ──────────────────────────
        hr = round(float(np.clip(
            np.random.normal(hr_m, hr_s)
            + rc * 1.8
            + (np.random.uniform(2, 7) if ev else 0),
            38, 130
        )), 1)

        # ── HRV ─────────────────────────────────────────
        rmssd = round(float(max(4.0,
            np.random.normal(max(5.0, rmssd_m), rmssd_s) - rc * 1.0
        )), 1)
        sdnn = round(float(max(rmssd * 1.05, rmssd * np.random.uniform(1.1, 1.45))), 1)

        # ── Rumia ────────────────────────────────────────
        prob_rum = min(max(0, p_rum) * (0.7 + 0.6 * c) * (0.2 if ev else 1), 1.0)
        hubo_rumia = int(np.random.random() < prob_rum)

        # ── Vocalización ─────────────────────────────────
        hubo_vocal = int(np.random.random() < min(p_voc + (0.1 if ev else 0), 1.0))

        # ── Movimiento / GPS ─────────────────────────────
        vel = round(float(max(0.0,
            np.random.normal(max(0.0, vel_m) * c, vel_s) * (0.3 if ev else 1)
        )), 2)
        metros = round(vel * (IVMIN / 60) * 1000, 1)

        paso = (vel / 3600) * IVMIN * 60 / 111320
        lat = float(np.clip(lat + np.random.normal(0, paso * 0.5), lat0 - radio, lat0 + radio))
        lon = float(np.clip(lon + np.random.normal(0, paso * 0.5), lon0 - radio, lon0 + radio))

        rows.append({
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

    return rows

# ─────────────────────────────────────────────
# GENERAR EL DATASET COMPLETO
# ─────────────────────────────────────────────
print("DAMP — Generador final con progresión temporal")
print(f"  {N_DIAS} días · intervalo {IVMIN} min · {NR} registros/animal")
print(f"  Progresión: sigmoide 48hs (Khatun 2017, Fogsgaard 2012)\n")

todos = []
for estado, cfg in RODEO.items():
    for aid in cfg["ids"]:
        filas = generar_animal(aid, estado, cfg)
        todos.extend(filas)
        infectado = f"infección en registro ~{cfg.get('inicio','—')}" if cfg["infectados"] else "sin infección"
        print(f"  ✓ BOV_{aid:03d}  [{estado:>10}]  {len(filas)} registros  ({infectado})")

df = pd.DataFrame(todos)

# ─────────────────────────────────────────────
# VALIDACIÓN
# ─────────────────────────────────────────────
print(f"\nShape: {df.shape[0]:,} filas × {df.shape[1]} columnas")

print("\n── Progresión de BOV_018 (clínica) — muestra cada 2hs ──")
bov18 = df[df.animal_id == "BOV_018"][
    ["timestamp", "progresion", "label",
     "temperatura_corporal_prom", "frec_cardiaca_prom", "rmssd"]
]
print(bov18.iloc[::24].head(20).to_string(index=False))

print("\n── Distribución de labels dinámicos ─────────────────")
print(df.groupby(["label_animal", "label"]).size().to_string())

print("\n── Promedios por label dinámico ──────────────────────")
cols = ["temperatura_corporal_prom", "frec_cardiaca_prom", "rmssd", "metros_recorridos"]
print(df.groupby("label")[cols].mean().round(2).to_string())

# ─────────────────────────────────────────────
# GUARDAR
# ─────────────────────────────────────────────
out = Path(__file__).resolve().parent
path_full   = out / "damp_data_temporal.csv"
path_sample = out / "damp_sample_temporal.csv"

df.to_csv(path_full, index=False)
df.sample(200, random_state=42).sort_values("timestamp").to_csv(path_sample, index=False)

# BOV_018 es clínica — tiene la progresión más completa
# sana → subclinica → clinica en 48hs, ideal para testear el modelo
path_test = out / "damp_data_test.csv"
vaca_test = df[df.animal_id == "BOV_018"].copy()
vaca_test.to_csv(path_test, index=False)

print(f"\n✓ Dataset completo  → {path_full}")
print(f"✓ Muestra 200 filas → {path_sample}")
print(f"✓ Test una vaca     → {path_test}")
print(f"  (BOV_018, clínica, {len(vaca_test)} registros)")
print(f"  labels: {vaca_test['label'].value_counts().to_dict()}")
print(f"\nColumnas: {list(df.columns)}")