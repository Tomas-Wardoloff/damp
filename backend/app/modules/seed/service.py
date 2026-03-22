"""
DAMP Seed Service — versión ajustada
- Nombres de vacas argentinas
- Coordenadas centradas en -34.591966, -60.887503 (±300m)
- Movimiento máximo 90m por tick (celo: hasta ~200m)
- GPS con movimiento visible en cada tick
- Readings futuros coherentes con historial de health (transiciones graduales)
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

# Centro del establecimiento — Alberti, Buenos Aires
CENTER_LAT = -34.591966
CENTER_LON = -60.887503

# 300m en grados ~ 0.002695° lat, ~0.003268° lon (a esta latitud)
RADIO_M    = 300          # metros, radio máximo del potrero
LAT_PER_M  = 1 / 111320  # grados lat por metro
LON_PER_M  = 1 / (111320 * math.cos(math.radians(CENTER_LAT)))

RADIO_LAT  = RADIO_M * LAT_PER_M   # ~0.002695°
RADIO_LON  = RADIO_M * LON_PER_M   # ~0.003268°

# Velocidad → metros por tick (5 min)
# max_vel para NO superar 90m/tick → 90m / (5min * 60s/min) * 3.6 = 1.08 km/h
# en realidad metros = vel_km_h * (5/60) * 1000 → max vel = 90/(5/60*1000) = 1.08 km/h
MAX_VEL_NORMAL = 1.08   # km/h → 90m/tick
MAX_VEL_CELO   = 2.40   # km/h → ~200m/tick (celo: >150m posible)

BREEDS = ["Holstein", "Jersey"]

# ─────────────────────────────────────────────
# PARÁMETROS FISIOLÓGICOS POR ESTADO
# (temp_m, temp_s, hr_m, hr_s, rmssd_m, rmssd_s, vel_m, vel_s, p_rum, p_voc)
# ─────────────────────────────────────────────
_PARAMS = {
    "sana":       (38.55, 0.45,  63.0, 7.0,  41.0, 6.5,  0.60, 0.25,  0.58, 0.07),
    "mastitis":   (40.20, 0.65,  87.0, 9.0,  18.0, 6.0,  0.22, 0.15,  0.12, 0.20),
    "celo":       (38.70, 0.45,  72.0, 7.5,  39.0, 6.5,  1.80, 0.50,  0.55, 0.25),
    "febril":     (39.90, 0.55,  76.0, 8.0,  33.0, 6.5,  0.45, 0.20,  0.45, 0.10),
    "digestivo":  (39.20, 0.55,  78.0, 8.5,  28.0, 6.5,  0.28, 0.15,  0.10, 0.18),
}
# vel_m ahora en km/h calibrado para que metros/tick queden en rango correcto:
# sana: 0.60 km/h → ~50m/tick   (rango normal: 20-80m)
# celo: 1.80 km/h → ~150m/tick  (puede superar 150m)
# enfermas: 0.22-0.45 km/h → 18-38m/tick (poco movimiento)

# ─────────────────────────────────────────────
# RODEO — 21 vacas
# ─────────────────────────────────────────────
RODEO = [
    (1,  "sana"),
    (2,  "sana"),
    (3,  "sana"),   # ex-febril
    (4,  "sana"),   # ex-mastitis
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
# HISTORIAL POR VACA
# (label, desde_hours_ago, hasta_hours_ago)
# ─────────────────────────────────────────────
_HISTORIAL: dict[int, list[tuple[str, int, int]]] = {
    1:  [("sana", 168, 0)],
    2:  [("sana", 168, 0)],
    # Vaca 3: tuvo fiebre hace 5 días, se recuperó — ciclo completo visible
    3:  [("sana", 168, 132), ("febril", 132, 96), ("sana", 96, 0)],
    # Vaca 4: tuvo mastitis hace 6 días, se recuperó — ciclo completo visible
    4:  [("sana", 168, 144), ("mastitis", 144, 90), ("sana", 90, 0)],
    # Vaca 5: tuvo digestivo hace 4 días, se recuperó — ciclo completo visible
    5:  [("sana", 168, 110), ("digestivo", 110, 74), ("sana", 74, 0)],
    # Vaca 6: tuvo fiebre leve hace 3 días, rápida recuperación
    6:  [("sana", 168, 80),  ("febril", 80, 56),    ("sana", 56, 0)],
    7:  [("sana", 168, 0)],
    8:  [("sana", 168, 0)],
    9:  [("sana", 168, 0)],
    10: [("sana", 168, 0)],
    11: [("sana", 168, 30),  ("celo", 30, 0)],
    12: [("sana", 168, 20),  ("celo", 20, 0)],
    13: [("sana", 168, 36),  ("celo", 36, 0)],
    14: [("sana", 168, 18),  ("celo", 18, 0)],
    15: [("sana", 168, 28),  ("celo", 28, 0)],
    16: [("sana", 168, 72),  ("mastitis", 72, 0)],
    17: [("sana", 168, 48),  ("mastitis", 48, 0)],
    18: [("sana", 168, 42),  ("febril", 42, 0)],
    19: [("sana", 168, 28),  ("febril", 28, 0)],
    20: [("sana", 168, 60),  ("digestivo", 60, 0)],
    21: [("sana", 168, 36),  ("digestivo", 36, 0)],
}

# ─────────────────────────────────────────────
# HISTORIAL "FUTURO" — qué pasa en las próximas 2.5 días
# Define la trayectoria clínica post-"ahora" coherente con el estado actual.
# hours_future = horas desde now (positivo = futuro)
# ─────────────────────────────────────────────
_HISTORIAL_FUTURO: dict[int, list[tuple[str, int, int]]] = {
    # Vacas sanas → se mantienen sanas
    1:  [("sana", 0, 60)],
    2:  [("sana", 0, 60)],
    # Vaca 3: ex-febril, ya recuperada → se mantiene sana
    3:  [("sana", 0, 60)],
    # Vaca 4: ex-mastitis, ya recuperada → se mantiene sana
    4:  [("sana", 0, 60)],
    5:  [("sana", 0, 60)],
    6:  [("sana", 0, 60)],
    7:  [("sana", 0, 60)],
    8:  [("sana", 0, 60)],
    9:  [("sana", 0, 60)],
    10: [("sana", 0, 60)],
    # Vacas en celo → celo dura ~30h totales, luego vuelven a sanas
    11: [("celo", 0, 10),  ("sana", 10, 60)],
    12: [("celo", 0, 20),  ("sana", 20, 60)],
    13: [("celo", 0, 6),   ("sana", 6, 60)],
    14: [("celo", 0, 22),  ("sana", 22, 60)],
    15: [("celo", 0, 12),  ("sana", 12, 60)],
    # Vacas con mastitis → empeoran un poco más, luego comienzan mejora gradual
    16: [("mastitis", 0, 24), ("febril", 24, 48), ("sana", 48, 60)],
    17: [("mastitis", 0, 18), ("febril", 18, 36), ("sana", 36, 60)],
    # Vacas febriles → pico de fiebre, luego bajan gradualmente
    18: [("febril", 0, 18), ("sana", 18, 60)],
    19: [("febril", 0, 12), ("sana", 12, 60)],
    # Vacas digestivas → empeoran, luego mejoran
    20: [("digestivo", 0, 20), ("febril", 20, 36), ("sana", 36, 60)],
    21: [("digestivo", 0, 14), ("febril", 14, 28), ("sana", 28, 60)],
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


def _label_at_hours_ago(cow_id: int, hours_ago: float) -> str:
    for seg_label, desde, hasta in _HISTORIAL.get(cow_id, [("sana", 999, 0)]):
        if hasta < hours_ago <= desde:
            return seg_label
    return "sana"


def _label_at_hours_future(cow_id: int, hours_future: float) -> str:
    """Label clínico para ticks en el futuro (hours_future >= 0)."""
    for seg_label, desde, hasta in _HISTORIAL_FUTURO.get(cow_id, [("sana", 0, 999)]):
        if desde <= hours_future < hasta:
            return seg_label
    return "sana"


def _label_at_tick(cow_id: int, ts: datetime, now: datetime) -> str:
    """Unifica pasado y futuro en un solo lookup."""
    delta_hours = (now - ts).total_seconds() / 3600
    if delta_hours >= 0:
        return _label_at_hours_ago(cow_id, delta_hours)
    else:
        return _label_at_hours_future(cow_id, -delta_hours)


def _transition_prog(ts: datetime, now: datetime, cow_id: int) -> float:
    """
    Factor 0-1 de 'qué tan dentro' del estado clínico actual está el tick.
    Sirve para interpolar suavemente entre estados en los readings futuros.
    Evita saltos bruscos en temperatura/HR al cambiar de label.
    """
    hours_future = (ts - now).total_seconds() / 3600
    if hours_future <= 0:
        return 1.0  # pasado: usa parámetros del label tal cual
    # En futuro, transición suave sigmoide (0→1 en las primeras 3h de un nuevo estado)
    # Buscamos hace cuántas horas empezó el segmento actual
    cur_label = _label_at_hours_future(cow_id, hours_future)
    # Buscar inicio del segmento
    for seg_label, desde, hasta in _HISTORIAL_FUTURO.get(cow_id, []):
        if seg_label == cur_label and desde <= hours_future < hasta:
            h_in_seg = hours_future - desde
            # sigmoid: 0 al inicio del seg, ~1 a las 3h
            return float(1 / (1 + math.exp(-1.2 * (h_in_seg - 1.5))))
    return 1.0


# ─────────────────────────────────────────────
# GENERADOR VECTORIZADO DE READINGS
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

    # Timestamps y horas del día
    timestamps = [start + timedelta(minutes=i * IV_MIN) for i in range(n)]
    hours_f    = np.array([ts.hour + ts.minute / 60.0 for ts in timestamps])

    # Factor circadiano vectorizado
    circ_arr = 0.55 + 0.45 * (
        np.exp(-0.5 * ((hours_f - 7.0) / 1.5) ** 2) +
        np.exp(-0.5 * ((hours_f - 17.0) / 1.5) ** 2)
    )

    # Factor nocturno (rumia y descanso)
    fn_night = np.exp(-0.5 * (np.minimum(
        np.abs(hours_f - 2), np.abs(hours_f - 2 + 24)) / 2.5) ** 2)

    # Label clínico por tick (pasado + futuro coherente)
    tick_labels     = np.array([_label_at_tick(cow_id, ts, now) for ts in timestamps])
    trans_progs     = np.array([_transition_prog(ts, now, cow_id) for ts in timestamps])

    # Parámetros base por tick
    p_matrix = np.array([_PARAMS[l] for l in tick_labels])
    temp_m  = p_matrix[:, 0];  temp_s  = p_matrix[:, 1]
    hr_m    = p_matrix[:, 2];  hr_s    = p_matrix[:, 3]
    rmssd_m = p_matrix[:, 4];  rmssd_s = p_matrix[:, 5]
    vel_m   = p_matrix[:, 6];  vel_s   = p_matrix[:, 7]
    p_rum   = p_matrix[:, 8];  p_voc   = p_matrix[:, 9]

    # Suavizado en transiciones futuras: interpola desde "sana" hacia el nuevo estado
    sana_p  = np.array(_PARAMS["sana"])
    # Para cada tick, mezcla entre parámetros sana y parámetros del label según trans_prog
    tp = trans_progs[:, np.newaxis]  # (n, 1)
    p_smooth = sana_p + tp * (p_matrix - sana_p)
    temp_m  = p_smooth[:, 0];  temp_s  = p_smooth[:, 1]
    hr_m    = p_smooth[:, 2];  hr_s    = p_smooth[:, 3]
    rmssd_m = p_smooth[:, 4];  rmssd_s = p_smooth[:, 5]
    vel_m   = p_smooth[:, 6];  vel_s   = p_smooth[:, 7]
    p_rum   = p_smooth[:, 8];  p_voc   = p_smooth[:, 9]

    # Ruido correlacionado entre sensores
    rc = rng.standard_normal(n)

    # Micro-eventos cross-class (~4%)
    micro_mask  = rng.random(n) < 0.04
    micro_type  = rng.integers(0, 4, n)
    micro_vals  = rng.uniform(0.3, 1.1, n)
    micro_temp  = np.where(micro_mask & (micro_type == 0), micro_vals * 0.8, 0.0)
    micro_hr    = np.where(micro_mask & (micro_type == 1), micro_vals * 12, 0.0)
    micro_rmssd = np.where(micro_mask & (micro_type == 2), -micro_vals * 10, 0.0)
    micro_rmssd+= np.where(micro_mask & (micro_type == 3),  micro_vals * 8,  0.0)

    # Temperatura
    temp_circ = 0.1 * np.sin(2 * np.pi * (hours_f - 6) / 24)
    temp_raw  = rng.normal(temp_m, temp_s) + temp_circ + rc * 0.08 + micro_temp
    temp      = np.clip(temp_raw, 36.5, 42.5).round(2)
    sensor_fail = rng.random(n) < 0.008
    temp        = np.where(sensor_fail, 38.6, temp)

    # HR
    hr_raw  = rng.normal(hr_m, hr_s) + rc * 1.5 + micro_hr
    artefact= rng.random(n) < 0.010
    hr_art  = rng.uniform(38, 48, n)
    hr      = np.where(artefact, hr_art, np.clip(hr_raw, 38, 130)).round(1)

    # HRV
    rmssd_raw = np.maximum(4.0, rng.normal(np.maximum(5.0, rmssd_m), rmssd_s) - rc * 0.8 + micro_rmssd)
    rmssd     = rmssd_raw.round(2)
    sdnn      = np.maximum(rmssd * 1.05, rmssd * rng.uniform(1.1, 1.45, n)).round(2)

    # Rumia — boost nocturno
    prob_rum_adj = np.clip(
        (rmssd_m / 40.0) * (0.5 + 0.5 * circ_arr + fn_night * 0.5) * p_rum,
        0.02, 0.95
    )
    hubo_rumia = (rng.random(n) < prob_rum_adj).astype(bool)

    # Vocalización
    prob_voc_adj = np.clip(0.07 + (temp_m - 38.6) / 2.0 * 0.20 + p_voc, 0.02, 0.95)
    hubo_vocal   = (rng.random(n) < prob_voc_adj).astype(bool)

    # ── VELOCIDAD CALIBRADA para no superar 90m/tick (normal) o 200m/tick (celo) ──
    is_celo   = (tick_labels == "celo")
    # Celo nocturno: movimiento amplificado entre 22hs y 3am
    hora_celo_factor = (
        np.exp(-0.5 * ((hours_f - 23) / 3.0) ** 2) +
        np.exp(-0.5 * ((hours_f -  1) / 2.5) ** 2)
    )
    vel_celo_boost = np.where(is_celo, 1.0 + hora_celo_factor * 0.8, 1.0)

    vel_base = vel_m * circ_arr * vel_celo_boost
    vel_raw  = np.maximum(0.0, rng.normal(vel_base, vel_s))

    # Clip estricto por condición para garantizar límites de metros/tick
    max_vel  = np.where(is_celo, MAX_VEL_CELO, MAX_VEL_NORMAL)
    vel      = np.minimum(vel_raw, max_vel).round(3)
    metros   = (vel * (IV_MIN / 60.0) * 1000.0).round(1)
    # Garantía explícita: 90m normal, 200m celo
    metros   = np.where(is_celo, np.minimum(metros, 200.0), np.minimum(metros, 90.0))

    # ── GPS — random walk dentro de ±300m del centro del establecimiento ──
    # Cada vaca tiene su punto de partida propio dentro del potrero
    offset_lat = rng.uniform(-RADIO_LAT * 0.5, RADIO_LAT * 0.5)
    offset_lon = rng.uniform(-RADIO_LON * 0.5, RADIO_LON * 0.5)
    lat0 = CENTER_LAT + offset_lat
    lon0 = CENTER_LON + offset_lon

    # Radio por estado: enfermas se mueven menos del potrero
    radio_lat = RADIO_LAT * {"sana": 0.8, "mastitis": 0.3, "celo": 1.0,
                              "febril": 0.5, "digestivo": 0.3}.get(label, 0.6)
    radio_lon = RADIO_LON * {"sana": 0.8, "mastitis": 0.3, "celo": 1.0,
                              "febril": 0.5, "digestivo": 0.3}.get(label, 0.6)

    gps_freeze     = int(rng.integers(80, 180)) if rng.random() < 0.25 else -1
    gps_freeze_len = int(rng.integers(5, 12))

    lat_arr = np.full(n, lat0)
    lon_arr = np.full(n, lon0)
    cur_lat, cur_lon = lat0, lon0

    for i in range(n):
        if gps_freeze > 0 and gps_freeze <= i < gps_freeze + gps_freeze_len:
            lat_arr[i] = cur_lat
            lon_arr[i] = cur_lon
        else:
            # paso en grados a partir de metros recorridos
            # garantiza movimiento visible entre ticks
            m_tick    = float(metros[i])
            paso_lat  = m_tick * LAT_PER_M * rng.normal(0, 0.6)
            paso_lon  = m_tick * LON_PER_M * rng.normal(0, 0.6)
            # mínimo 2m de desplazamiento para que siempre haya movimiento visible
            if abs(paso_lat) < 2 * LAT_PER_M:
                paso_lat = float(rng.choice([-1, 1])) * 2 * LAT_PER_M * rng.uniform(0.5, 1.5)
            if abs(paso_lon) < 2 * LON_PER_M:
                paso_lon = float(rng.choice([-1, 1])) * 2 * LON_PER_M * rng.uniform(0.5, 1.5)

            cur_lat = float(np.clip(cur_lat + paso_lat, CENTER_LAT - radio_lat, CENTER_LAT + radio_lat))
            cur_lon = float(np.clip(cur_lon + paso_lon, CENTER_LON - radio_lon, CENTER_LON + radio_lon))
            lat_arr[i] = cur_lat
            lon_arr[i] = cur_lon

    return [
        {
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
        }
        for i in range(n)
    ]


# ─────────────────────────────────────────────
# GENERADOR DE HEALTH ANALYSES
# Solo hacia atrás (7 días), sin cambios en la lógica original
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
            breed = BREEDS[row_idx % len(BREEDS)]
            cow = Cow(
                name=breed,
                breed=breed,
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
                cow_id=cow_id, collar_id=collar_id,
                label=label, start=start, n=n, now=now,
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
                f"Seed OK — {cows_created} vacas, {collars_created} collares, "
                f"{readings_created:,} readings "
                f"({BACK_READINGS}d atrás → {FORWARD_READINGS}d adelante), "
                f"{analyses_created:,} health analyses "
                f"({BACK_HEALTH} días, 1/hora)"
            ),
        }