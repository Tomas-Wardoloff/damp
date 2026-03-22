"""
DAMP Seed Service — v3
Parámetros biológicos idénticos al generador de entrenamiento (generator.py).
Coordenadas: campo real en -34.591966, -60.887503, radio 300m.
Velocidad máxima: 90m/5min sana/enferma, >150m/5min celo.
Nombres: razas lecheras argentinas reales.
Readings futuros: progresión coherente con el historial de health.
"""

import math
import random
from datetime import datetime, timedelta

import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.collar.models import Collar
from app.modules.cow.models import Cow
from app.modules.health.models import HealthAnalysis
from app.modules.reading.models import Reading
from app.shared.enums import HealthStatus

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
IV_MIN           = 5
BACK_READINGS    = 1
FORWARD_READINGS = 2.5
BACK_HEALTH      = 7
RANDOM_SEED      = 42

# Campo real — San Antonio de Areco, Buenos Aires
LAT_CENTRO =  -34.591966
LON_CENTRO =  -60.887503
RADIO_M    =   300.0        # metros máximos desde el centro
RADIO_DEG  =   RADIO_M / 111320.0  # ~0.002696 grados

# Velocidad máxima en metros por tick (5 min)
MAX_METROS_NORMAL = 90.0   # sana / enferma
MAX_METROS_CELO   = 350.0  # celo puede moverse mucho más

# ─────────────────────────────────────────────
# RAZAS LECHERAS ARGENTINAS REALES
# ─────────────────────────────────────────────
NOMBRES_RAZAS = [
    "Holando Argentino",
    "Jersey",
    "Pardo Suizo Americano",
    "Ayrshire",
    "Shorthorn Lechero",
    "Lincoln",
    "Holando Argentino",   # la más común, se repite
    "Jersey",
    "Pardo Suizo Americano",
    "Holando Argentino",
]

# ─────────────────────────────────────────────
# PARÁMETROS BASE — idénticos al generator.py de entrenamiento
# ─────────────────────────────────────────────
BASE = {
    "temp":    38.6,  "temp_s":   0.55,
    "hr":      65.0,  "hr_s":    11.0,
    "rmssd":   40.0,  "rmssd_s": 13.0,
    "vel":      1.7,  "vel_s":    1.00,
    "p_rumia": 0.52,
    "p_vocal": 0.07,
}

DELTAS = {
    "sana":      {"temp": 0.0,  "hr":  0.0,  "rmssd":   0.0,  "vel":  0.0,  "p_rumia":  0.0,  "p_vocal":  0.0,  "max_prog": 0.0},
    "mastitis":  {"temp": +1.8, "hr": +24.0, "rmssd": -26.0,  "vel": -1.10, "p_rumia": -0.42, "p_vocal": +0.20, "max_prog": 1.0},
    "celo":      {"temp": +0.2, "hr":  +9.0, "rmssd":  -4.0,  "vel": +2.80, "p_rumia": -0.05, "p_vocal": +0.22, "max_prog": 1.0},
    "febril":    {"temp": +1.7, "hr": +14.0, "rmssd":  -8.0,  "vel": -0.25, "p_rumia": -0.15, "p_vocal": +0.10, "max_prog": 1.0},
    "digestivo": {"temp": +0.8, "hr": +16.0, "rmssd": -14.0,  "vel": -0.90, "p_rumia": -0.44, "p_vocal": +0.22, "max_prog": 1.0},
}

# ─────────────────────────────────────────────
# RODEO — 21 vacas
# ─────────────────────────────────────────────
RODEO = [
    (1,  "sana"),
    (2,  "sana"),
    (3,  "sana"),      # ex-febril: tuvo fiebre hace 5-3 días, ahora recovering
    (4,  "sana"),      # ex-mastitis: tuvo mastitis hace 6-4 días, ahora recovering
    (5,  "sana"),
    (6,  "sana"),
    (7,  "sana"),
    (8,  "sana"),
    (9,  "sana"),
    (10, "sana"),
    (11, "celo"),
    (12, "celo"),
    (13, "celo"),
    (14, "celo"),
    (15, "celo"),
    (16, "mastitis"),
    (17, "mastitis"),
    (18, "febril"),
    (19, "febril"),
    (20, "digestivo"),
    (21, "digestivo"),
]

# ─────────────────────────────────────────────
# HISTORIAL POR VACA (hours_ago desde NOW)
# Segmentos: (label, desde_hours_ago, hasta_hours_ago)
# ─────────────────────────────────────────────
_HISTORIAL: dict[int, list[tuple[str, int, int]]] = {
    1:  [("sana",      168,   0)],
    2:  [("sana",      168,   0)],
    3:  [("sana",      168, 120), ("febril",    120,  72), ("sana",      72,   0)],
    4:  [("sana",      168, 144), ("mastitis",  144,  96), ("sana",      96,   0)],
    5:  [("sana",      168,   0)],
    6:  [("sana",      168,   0)],
    7:  [("sana",      168,   0)],
    8:  [("sana",      168,   0)],
    9:  [("sana",      168,   0)],
    10: [("sana",      168,   0)],
    11: [("sana",      168,  30), ("celo",       30,   0)],
    12: [("sana",      168,  20), ("celo",       20,   0)],
    13: [("sana",      168,  36), ("celo",       36,   0)],
    14: [("sana",      168,  18), ("celo",       18,   0)],
    15: [("sana",      168,  28), ("celo",       28,   0)],
    16: [("sana",      168,  72), ("mastitis",   72,   0)],
    17: [("sana",      168,  48), ("mastitis",   48,   0)],
    18: [("sana",      168,  42), ("febril",     42,   0)],
    19: [("sana",      168,  28), ("febril",     28,   0)],
    20: [("sana",      168,  60), ("digestivo",  60,   0)],
    21: [("sana",      168,  36), ("digestivo",  36,   0)],
}

# Cuántas horas más se espera que dure cada condición activa
# Usado para generar readings futuros coherentes
_DURACION_FUTURA: dict[int, int] = {
    3:  30,   # recovering: leve fiebre residual unas horas más
    4:  20,   # recovering: levemente comprometida aún
    11: 18,   # celo dura ~18hs más
    12: 8,    # celo casi terminando
    13: 30,   # celo activo
    14: 6,    # celo casi terminando
    15: 20,   # celo
    16: 48,   # mastitis moderada, seguirá varios días
    17: 36,   # mastitis severa
    18: 24,   # fiebre durará ~1 día más
    19: 16,   # fiebre casi pasando
    20: 36,   # digestivo
    21: 20,   # digestivo casi pasando
}

_LABEL_TO_STATUS = {
    "sana":       HealthStatus.SANA,
    "mastitis":   HealthStatus.MASTITIS,
    "celo":       HealthStatus.CELO,
    "febril":     HealthStatus.FEBRIL,
    "digestivo":  HealthStatus.DIGESTIVO,
}

_SECONDARY_MAP = {
    HealthStatus.SANA:       HealthStatus.FEBRIL,
    HealthStatus.MASTITIS:   HealthStatus.FEBRIL,
    HealthStatus.CELO:       HealthStatus.SANA,
    HealthStatus.FEBRIL:     HealthStatus.MASTITIS,
    HealthStatus.DIGESTIVO:  HealthStatus.MASTITIS,
}


# ─────────────────────────────────────────────
# HELPERS — idénticos al generator.py
# ─────────────────────────────────────────────
def _circ(h: float) -> float:
    return 0.55 + 0.45 * (
        math.exp(-0.5 * ((h - 7) / 1.5) ** 2) +
        math.exp(-0.5 * ((h - 17) / 1.5) ** 2)
    )

def _factor_nocturno(h: float) -> float:
    d = min(abs(h - 2), abs(h - 2 + 24), abs(h - 2 - 24))
    return math.exp(-0.5 * (d / 2.5) ** 2)

def _sigmoide(i: int, inicio: int, pendiente: float = 0.2, centro: float = 24.0) -> float:
    h = (i - inicio) * IV_MIN / 60.0
    return 0.0 if h <= 0 else 1 / (1 + math.exp(-pendiente * (h - centro)))

def _label_at_hours_ago(cow_id: int, hours_ago: float) -> str:
    for seg_label, desde, hasta in _HISTORIAL.get(cow_id, [("sana", 999, 0)]):
        if hasta < hours_ago <= desde:
            return seg_label
    return "sana"

def _label_future(cow_id: int, hours_from_now: float) -> str:
    """
    Qué label aplica en el futuro, dado cuántas horas desde ahora.
    Una vez que una condición termina su duración esperada → sana.
    Las vacas recovering (3, 4) parten de síntomas leves y se recuperan.
    """
    duracion = _DURACION_FUTURA.get(cow_id, 0)
    label_actual = _label_at_hours_ago(cow_id, 0.01)  # estado actual

    if label_actual == "sana":
        return "sana"

    # Si ya pasó la duración esperada → sana
    if hours_from_now > duracion:
        return "sana"

    # Recovering: reducen síntomas gradualmente
    if cow_id in (3, 4):
        return "febril" if cow_id == 3 else "mastitis"

    return label_actual


# ─────────────────────────────────────────────
# PROGRESIÓN BIOLÓGICA POR TICK
# Devuelve (prog, d) donde prog es 0-1 y d son los deltas de la clase
# Para readings futuros: prog decrece si se está recuperando
# ─────────────────────────────────────────────
def _prog_and_delta(cow_id: int, label: str, hours_offset: float, is_future: bool):
    """
    hours_offset: horas desde el inicio del segmento activo
    is_future: True si el tick es en el futuro (se aplica recuperación)
    """
    d = DELTAS.get(label, DELTAS["sana"])

    if label == "sana":
        return 0.0, d

    if is_future:
        duracion = _DURACION_FUTURA.get(cow_id, 24)
        if duracion == 0:
            return 0.0, DELTAS["sana"]
        # Progresión decreciente: empieza en el nivel actual y baja a 0
        t = max(0.0, 1.0 - hours_offset / duracion)
        # Para recovering (3, 4): empiezan ya en progresión baja
        if cow_id in (3, 4):
            t = t * 0.35   # síntomas leves residuales
        prog = min(t * d["max_prog"], d["max_prog"])
    else:
        # Pasado: progresión completa al estado actual
        prog = d["max_prog"] * 0.85   # estado consolidado

    return prog, d


# ─────────────────────────────────────────────
# GENERADOR VECTORIZADO DE UN SEGMENTO DE READINGS
# ─────────────────────────────────────────────
def _gen_segment(
    rng: np.random.Generator,
    cow_id: int,
    collar_id: int,
    label: str,
    timestamps: list,
    hours_offsets: np.ndarray,   # horas desde inicio del segmento
    is_future: bool,
    lat_arr: np.ndarray,
    lon_arr: np.ndarray,
) -> list[dict]:
    n = len(timestamps)
    if n == 0:
        return []

    hours_f = np.array([ts.hour + ts.minute / 60.0 for ts in timestamps])
    circ_v  = 0.55 + 0.45 * (
        np.exp(-0.5 * ((hours_f - 7.0) / 1.5) ** 2) +
        np.exp(-0.5 * ((hours_f - 17.0) / 1.5) ** 2)
    )
    fn_v = np.array([_factor_nocturno(h) for h in hours_f])

    # Construir prog por tick
    progs = np.array([_prog_and_delta(cow_id, label, h, is_future)[0] for h in hours_offsets])
    d = DELTAS.get(label, DELTAS["sana"])

    temp_m  = BASE["temp"]    + progs * d["temp"]
    hr_m    = BASE["hr"]      + progs * d["hr"]
    rmssd_m = BASE["rmssd"]   + progs * d["rmssd"]
    vel_m   = BASE["vel"]     + progs * d["vel"]
    p_rum   = BASE["p_rumia"] + progs * d["p_rumia"]
    p_voc   = BASE["p_vocal"] + progs * d["p_vocal"]

    temp_s  = BASE["temp_s"]  * (1 + 0.4 * progs)
    hr_s    = BASE["hr_s"]    * (1 + 0.5 * progs)
    rmssd_s = BASE["rmssd_s"] * (1 + 0.3 * progs)
    vel_s   = BASE["vel_s"]   * (1 + 0.3 * progs)

    rc = rng.standard_normal(n)

    # Temperatura con circadiano y nocturno
    temp_circ = 0.1 * np.sin(2 * np.pi * (hours_f - 6) / 24) - fn_v * 0.25
    temp = np.clip(rng.normal(temp_m, temp_s) + temp_circ + rc * 0.08, 36.5, 42.5).round(2)
    temp = np.where(rng.random(n) < 0.008, 38.6, temp)

    # HR con nocturno
    hr_circ = -fn_v * 7.0
    hr_raw  = np.clip(rng.normal(hr_m + hr_circ, hr_s) + rc * 1.8, 38, 130)
    hr = np.where(rng.random(n) < 0.010, rng.uniform(38, 48, n), hr_raw).round(1)

    # HRV con nocturno (RMSSD sube de noche)
    rmssd_base = np.maximum(5.0, rmssd_m + fn_v * 8.0)
    rmssd = np.maximum(4.0, rng.normal(rmssd_base, rmssd_s) - rc * 1.0).round(1)
    sdnn  = np.maximum(rmssd * 1.05, rmssd * rng.uniform(1.1, 1.45, n)).round(1)

    # Rumia — mayor de noche
    rum_noche = 1.0 + fn_v * 0.6
    prob_rum  = np.clip(np.maximum(0, p_rum) * (0.5 + 0.5 * circ_v + fn_v * 0.5) * rum_noche, 0.02, 1.0)
    hubo_rumia = (rng.random(n) < prob_rum)

    # Vocalización
    prob_voc  = np.clip(0.07 + (temp_m - 38.6) / 2.0 * 0.20 + p_voc, 0.02, 0.95)
    hubo_vocal= (rng.random(n) < prob_voc)

    # Velocidad — nocturno reduce fuertemente, celo amplifica de noche
    if label == "celo":
        hora_celo = (np.exp(-0.5 * ((hours_f - 23) / 3.0) ** 2) +
                     np.exp(-0.5 * ((hours_f - 1)  / 2.5) ** 2))
        vel_m_adj = vel_m + hora_celo * progs * 1.8
        vel_noche = np.maximum(0.0, vel_m_adj * (1 - fn_v * 0.3))  # celo no duerme tanto
    else:
        vel_noche = np.maximum(0.0, vel_m * circ_v * (1 - fn_v * 0.85))

    vel_raw = np.maximum(0.0, rng.normal(vel_noche, vel_s * (1 - fn_v * 0.5)))

    # ── Convertir vel (km/h) a metros por tick y aplicar límites ──
    metros_raw = vel_raw * (IV_MIN / 60) * 1000
    if label == "celo":
        metros_clipped = np.minimum(metros_raw, MAX_METROS_CELO)
    else:
        metros_clipped = np.minimum(metros_raw, MAX_METROS_NORMAL)

    # Recalcular vel desde metros ya limitados
    vel = (metros_clipped / ((IV_MIN / 60) * 1000)).round(2)
    metros = metros_clipped.round(1)

    # GPS — actualizar lat/lon ya pasados como arrays
    rows = []
    for i in range(n):
        rows.append({
            "timestamp":                 timestamps[i],
            "cow_id":                    cow_id,
            "collar_id":                 collar_id,
            "temperatura_corporal_prom": float(temp[i]),
            "hubo_rumia":                bool(hubo_rumia[i]),
            "frec_cardiaca_prom":        float(hr[i]),
            "rmssd":                     float(rmssd[i]),
            "sdnn":                      float(sdnn[i]),
            "hubo_vocalizacion":         bool(hubo_vocal[i]),
            "latitud":                   round(float(lat_arr[i]), 6),
            "longitud":                  round(float(lon_arr[i]), 6),
            "metros_recorridos":         float(metros[i]),
            "velocidad_movimiento_prom": float(vel[i]),
        })
    return rows


def _build_gps_track(rng: np.random.Generator, label: str, metros: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Construye el track GPS completo para una vaca.
    Parte de un punto aleatorio dentro del campo (300m del centro)
    y hace random walk limitado a RADIO_DEG del centro.
    """
    n = len(metros)
    # Punto de partida: dentro del campo pero no siempre en el centro
    offset_lat = rng.uniform(-RADIO_DEG * 0.7, RADIO_DEG * 0.7)
    offset_lon = rng.uniform(-RADIO_DEG * 0.7, RADIO_DEG * 0.7)
    lat0 = LAT_CENTRO + offset_lat
    lon0 = LON_CENTRO + offset_lon

    lat_arr = np.empty(n)
    lon_arr = np.empty(n)
    cur_lat, cur_lon = lat0, lon0

    for i in range(n):
        m = float(metros[i])
        if m < 0.5:
            # Animal quieto — pequeño jitter de GPS
            cur_lat += rng.normal(0, 0.000002)
            cur_lon += rng.normal(0, 0.000002)
        else:
            paso = m / 111320.0
            cur_lat += rng.normal(0, paso * 0.6)
            cur_lon += rng.normal(0, paso * 0.6)

        # Clip dentro del radio del campo
        cur_lat = float(np.clip(cur_lat, LAT_CENTRO - RADIO_DEG, LAT_CENTRO + RADIO_DEG))
        cur_lon = float(np.clip(cur_lon, LON_CENTRO - RADIO_DEG, LON_CENTRO + RADIO_DEG))
        lat_arr[i] = cur_lat
        lon_arr[i] = cur_lon

    return lat_arr, lon_arr


# ─────────────────────────────────────────────
# GENERADOR COMPLETO DE READINGS POR VACA
# ─────────────────────────────────────────────
def _generate_readings_fast(
    cow_id: int,
    collar_id: int,
    label: str,
    start: datetime,
    n: int,
    now: datetime,
) -> list[dict]:
    rng = np.random.default_rng(RANDOM_SEED + cow_id)

    timestamps = [start + timedelta(minutes=i * IV_MIN) for i in range(n)]
    hours_ago  = np.array([(now - ts).total_seconds() / 3600 for ts in timestamps])

    # Label fisiológico por tick
    tick_labels = []
    hours_offsets = []
    for i, (ts, h_ago) in enumerate(zip(timestamps, hours_ago)):
        if h_ago > 0:
            # Pasado: usar historial
            lbl = _label_at_hours_ago(cow_id, h_ago)
            tick_labels.append(lbl)
            # Horas desde que arrancó el segmento actual
            hours_offsets.append(max(0.0, -h_ago))
        else:
            # Futuro: usar progresión futura
            h_from_now = abs(float(h_ago))
            lbl = _label_future(cow_id, h_from_now)
            tick_labels.append(lbl)
            hours_offsets.append(h_from_now)

    tick_labels   = np.array(tick_labels)
    hours_offsets = np.array(hours_offsets)
    is_future     = hours_ago <= 0

    # Generar metros primero para construir el GPS
    # Velocidad base por tick según label
    all_rows = []
    n_ticks  = len(timestamps)

    # Construir metros aproximados para GPS (sin ruido complejo, solo para el track)
    vel_base_approx = np.array([
        (BASE["vel"] + DELTAS.get(lbl, DELTAS["sana"])["vel"] * 0.8)
        for lbl in tick_labels
    ])
    hours_f_approx = np.array([ts.hour + ts.minute / 60.0 for ts in timestamps])
    circ_approx = 0.55 + 0.45 * (
        np.exp(-0.5 * ((hours_f_approx - 7) / 1.5) ** 2) +
        np.exp(-0.5 * ((hours_f_approx - 17) / 1.5) ** 2)
    )
    fn_approx = np.array([_factor_nocturno(h) for h in hours_f_approx])
    metros_approx = np.maximum(0, vel_base_approx * circ_approx * (1 - fn_approx * 0.85)) * (IV_MIN / 60) * 1000

    # Aplicar límites
    is_celo_mask = tick_labels == "celo"
    metros_approx = np.where(is_celo_mask,
                              np.minimum(metros_approx, MAX_METROS_CELO),
                              np.minimum(metros_approx, MAX_METROS_NORMAL))

    lat_arr, lon_arr = _build_gps_track(rng, label, metros_approx)

    # Generar sensores por segmento coherente
    all_rows = _gen_segment(
        rng=rng,
        cow_id=cow_id,
        collar_id=collar_id,
        label=label,
        timestamps=timestamps,
        hours_offsets=hours_offsets,
        is_future=is_future.any(),
        lat_arr=lat_arr,
        lon_arr=lon_arr,
    )

    return all_rows


# ─────────────────────────────────────────────
# HEALTH ANALYSES — 7 días para atrás, 1/hora
# ─────────────────────────────────────────────
def _generate_health_analyses(cow_id: int, label: str, now: datetime) -> list[dict]:
    rng = random.Random(cow_id * 999)
    rows = []
    for hours_ago in range(BACK_HEALTH * 24, 0, -1):
        seg_label        = _label_at_hours_ago(cow_id, hours_ago)
        primary_status   = _LABEL_TO_STATUS.get(seg_label, HealthStatus.SANA)
        secondary_status = _SECONDARY_MAP.get(primary_status, HealthStatus.SANA)
        primary_conf     = round(rng.uniform(0.55, 0.92), 4)
        residuo          = round(rng.uniform(0.01, 0.08), 4)
        secondary_conf   = max(0.01, round(1.0 - primary_conf - residuo, 4))

        rows.append({
            "cow_id":               cow_id,
            "model_cow_id":         str(cow_id),
            "status":               primary_status,
            "confidence":           primary_conf,
            "primary_status":       primary_status,
            "primary_confidence":   primary_conf,
            "secondary_status":     secondary_status,
            "secondary_confidence": secondary_conf,
            "alert":                primary_status != HealthStatus.SANA,
            "n_readings_used":      80,
            "created_at":           now - timedelta(hours=hours_ago),
        })
    return rows


# ─────────────────────────────────────────────
# RESET
# ─────────────────────────────────────────────
def _truncate_and_reset(db: Session) -> None:
    db.execute(text("TRUNCATE TABLE health_analyses RESTART IDENTITY CASCADE"))
    db.execute(text("TRUNCATE TABLE readings RESTART IDENTITY CASCADE"))
    db.execute(text("TRUNCATE TABLE collars RESTART IDENTITY CASCADE"))
    db.execute(text("TRUNCATE TABLE cows RESTART IDENTITY CASCADE"))
    db.commit()


# ─────────────────────────────────────────────
# SERVICIO PRINCIPAL
# ─────────────────────────────────────────────
class SeedService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_readings(self) -> dict:
        now   = datetime.utcnow().replace(second=0, microsecond=0)
        now   = now - timedelta(minutes=now.minute % IV_MIN)
        start = now - timedelta(days=BACK_READINGS)
        end   = now + timedelta(days=FORWARD_READINGS)
        n     = int((end - start).total_seconds() / 60 // IV_MIN)

        _truncate_and_reset(self.db)
        random.seed(RANDOM_SEED)

        cows_created     = 0
        collars_created  = 0
        readings_created = 0
        analyses_created = 0

        # ── Paso 1: cows + collars ──────────────────────────────
        cow_collar_map: list[tuple[int, int, str]] = []
        for row_idx, (cow_num, label) in enumerate(RODEO):
            cow = Cow(
                breed=NOMBRES_RAZAS[row_idx % len(NOMBRES_RAZAS)],
                registration_date=datetime.utcnow(),
                age_months=random.randint(18, 84),
            )
            self.db.add(cow)
            self.db.flush()

            collar = Collar(
                assigned_cow_id=cow.id,
                assigned_at=datetime.utcnow(),
                unassigned_at=None,
            )
            self.db.add(collar)
            self.db.flush()

            cow_collar_map.append((cow.id, collar.id, label))
            cows_created    += 1
            collars_created += 1

        self.db.commit()

        # ── Paso 2: readings ────────────────────────────────────
        for cow_id, collar_id, label in cow_collar_map:
            rows = _generate_readings_fast(
                cow_id=cow_id,
                collar_id=collar_id,
                label=label,
                start=start,
                n=n,
                now=now,
            )
            self.db.execute(
                text("""
                    INSERT INTO readings
                        (timestamp, cow_id, collar_id,
                         temperatura_corporal_prom, hubo_rumia,
                         frec_cardiaca_prom, rmssd, sdnn, hubo_vocalizacion,
                         latitud, longitud, metros_recorridos,
                         velocidad_movimiento_prom)
                    VALUES
                        (:timestamp, :cow_id, :collar_id,
                         :temperatura_corporal_prom, :hubo_rumia,
                         :frec_cardiaca_prom, :rmssd, :sdnn, :hubo_vocalizacion,
                         :latitud, :longitud, :metros_recorridos,
                         :velocidad_movimiento_prom)
                """),
                rows,
            )
            readings_created += len(rows)

        self.db.commit()

        # ── Paso 3: health analyses ─────────────────────────────
        for seq, (_cow_num, label) in enumerate(RODEO):
            cow_id = seq + 1
            rows   = _generate_health_analyses(cow_id=cow_id, label=label, now=now)
            self.db.execute(
                text("""
                    INSERT INTO health_analyses
                        (cow_id, model_cow_id, status, confidence,
                         primary_status, primary_confidence,
                         secondary_status, secondary_confidence,
                         alert, n_readings_used, created_at)
                    VALUES
                        (:cow_id, :model_cow_id, :status, :confidence,
                         :primary_status, :primary_confidence,
                         :secondary_status, :secondary_confidence,
                         :alert, :n_readings_used, :created_at)
                """),
                rows,
            )
            analyses_created += len(rows)

        self.db.commit()

        return {
            "cows_created":      cows_created,
            "collars_created":   collars_created,
            "readings_created":  readings_created,
            "analyses_created":  analyses_created,
            "message": (
                f"Seed OK — {cows_created} vacas ({', '.join(set(r[1] for r in RODEO))}), "
                f"{readings_created:,} readings "
                f"({BACK_READINGS}d atrás → {FORWARD_READINGS}d adelante), "
                f"{analyses_created:,} health analyses ({BACK_HEALTH} días)"
            ),
        }