"""
DAMP Seed Service
Reset + recarga de cows, collars, readings y health_analyses.

Vacas: 21 — estado actual: 10 sana, 5 celo, 2 mastitis, 2 febril, 2 digestivo
GPS:   campo en -34.591966, -60.887503, radio 200m
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

LAT_CENTRO = -34.591966
LON_CENTRO = -60.887503
RADIO_DEG  = 200.0 / 111320.0   # 200 metros en grados

BREEDS = [
    "Holando Argentino", "Jersey", "Pardo Suizo Americano",
    "Ayrshire", "Shorthorn Lechero", "Holando Argentino",
    "Jersey", "Holando Argentino", "Pardo Suizo Americano", "Holando Argentino",
]

# ─────────────────────────────────────────────
# PARÁMETROS — mismos que el generador de entrenamiento
# ─────────────────────────────────────────────
_PARAMS = {
    "sana":       (38.55, 0.55,  63.0, 11.0,  41.0, 13.0,  1.5, 1.0,  0.52, 0.07),
    "mastitis":   (40.40, 0.75,  89.0, 12.0,  14.0,  8.0,  0.6, 0.5,  0.10, 0.27),
    "celo":       (38.75, 0.55,  74.0, 10.0,  36.0, 10.0,  4.5, 1.2,  0.47, 0.29),
    "febril":     (40.30, 0.65,  79.0, 10.0,  32.0, 10.0,  1.3, 0.7,  0.37, 0.17),
    "digestivo":  (39.40, 0.65,  81.0, 11.0,  26.0, 10.0,  0.8, 0.5,  0.08, 0.25),
}

# ─────────────────────────────────────────────
# RODEO — 21 vacas
# ─────────────────────────────────────────────
RODEO = [
    (1,  "sana"),
    (2,  "sana"),
    (3,  "sana"),      # ex-febril
    (4,  "sana"),      # ex-mastitis
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


def _factor_nocturno(h: float) -> float:
    d = min(abs(h - 2), abs(h - 2 + 24), abs(h - 2 - 24))
    return math.exp(-0.5 * (d / 2.5) ** 2)


# ─────────────────────────────────────────────
# GENERADOR VECTORIZADO
# ─────────────────────────────────────────────
def _generate_readings_fast(
    cow_id: int, collar_id: int, label: str,
    start: datetime, n: int, now: datetime,
) -> list[dict]:
    rng = np.random.default_rng(RANDOM_SEED + cow_id)

    timestamps = [start + timedelta(minutes=i * IV_MIN) for i in range(n)]
    hours_ago  = np.array([(now - ts).total_seconds() / 3600 for ts in timestamps])
    hours_f    = np.array([ts.hour + ts.minute / 60.0 for ts in timestamps])

    # Label por tick según historial
    tick_labels = np.array([_label_at_hours_ago(cow_id, float(h)) for h in hours_ago])

    # Parámetros por tick
    p_matrix = np.array([_PARAMS[l] for l in tick_labels])
    temp_m  = p_matrix[:, 0];  temp_s  = p_matrix[:, 1]
    hr_m    = p_matrix[:, 2];  hr_s    = p_matrix[:, 3]
    rmssd_m = p_matrix[:, 4];  rmssd_s = p_matrix[:, 5]
    vel_m   = p_matrix[:, 6];  vel_s   = p_matrix[:, 7]
    p_rum   = p_matrix[:, 8];  p_voc   = p_matrix[:, 9]

    circ_v = 0.55 + 0.45 * (
        np.exp(-0.5 * ((hours_f - 7.0) / 1.5) ** 2) +
        np.exp(-0.5 * ((hours_f - 17.0) / 1.5) ** 2)
    )
    fn_v = np.array([_factor_nocturno(h) for h in hours_f])
    rc   = rng.standard_normal(n)

    # Micro-eventos cross-class (~5%)
    micro_mask  = rng.random(n) < 0.05
    micro_type  = rng.integers(0, 4, n)
    micro_vals  = rng.uniform(0.3, 1.1, n)
    micro_temp  = np.where(micro_mask & (micro_type == 0), micro_vals * 0.8,  0.0)
    micro_hr    = np.where(micro_mask & (micro_type == 1), micro_vals * 12,   0.0)
    micro_rmssd = np.where(micro_mask & (micro_type == 2), -micro_vals * 10,  0.0)
    micro_rmssd+= np.where(micro_mask & (micro_type == 3),  micro_vals * 8,   0.0)

    # Temperatura
    temp_circ = 0.1 * np.sin(2 * np.pi * (hours_f - 6) / 24) - fn_v * 0.25
    temp = np.clip(rng.normal(temp_m, temp_s) + temp_circ + rc * 0.08 + micro_temp, 36.5, 42.5).round(2)
    temp = np.where(rng.random(n) < 0.008, 38.6, temp)

    # HR
    hr_raw = np.clip(rng.normal(hr_m - fn_v * 7.0, hr_s) + rc * 1.8 + micro_hr, 38, 130)
    hr = np.where(rng.random(n) < 0.010, rng.uniform(38, 48, n), hr_raw).round(1)

    # HRV
    rmssd = np.maximum(4.0, rng.normal(np.maximum(5.0, rmssd_m + fn_v * 8.0), rmssd_s) - rc * 1.0 + micro_rmssd).round(1)
    sdnn  = np.maximum(rmssd * 1.05, rmssd * rng.uniform(1.1, 1.45, n)).round(1)

    # Rumia
    rum_noche = 1.0 + fn_v * 0.6
    prob_rum  = np.clip(np.maximum(0, p_rum) * (0.5 + 0.5 * circ_v + fn_v * 0.5) * rum_noche, 0.02, 1.0)
    hubo_rumia = (rng.random(n) < prob_rum)

    # Vocalización
    hubo_vocal = (rng.random(n) < np.clip(p_voc, 0.02, 0.95))

    # Velocidad
    is_celo = tick_labels == "celo"
    vel_base = np.where(is_celo, vel_m, vel_m * circ_v * (1 - fn_v * 0.85))
    vel = np.maximum(0.0, rng.normal(vel_base, vel_s * (1 - fn_v * 0.5))).round(2)
    metros = (vel * (IV_MIN / 60) * 1000).round(1)

    # GPS — punto de partida dentro del radio de 200m del centro
    lat0 = LAT_CENTRO + rng.uniform(-RADIO_DEG * 0.8, RADIO_DEG * 0.8)
    lon0 = LON_CENTRO + rng.uniform(-RADIO_DEG * 0.8, RADIO_DEG * 0.8)
    cur_lat, cur_lon = float(lat0), float(lon0)

    lat_out = np.empty(n)
    lon_out = np.empty(n)
    for i in range(n):
        m = float(metros[i])
        if m < 0.5:
            cur_lat += float(rng.normal(0, 0.000002))
            cur_lon += float(rng.normal(0, 0.000002))
        else:
            paso = m / 111320.0
            cur_lat += float(rng.normal(0, paso * 0.6))
            cur_lon += float(rng.normal(0, paso * 0.6))
        cur_lat = float(np.clip(cur_lat, LAT_CENTRO - RADIO_DEG, LAT_CENTRO + RADIO_DEG))
        cur_lon = float(np.clip(cur_lon, LON_CENTRO - RADIO_DEG, LON_CENTRO + RADIO_DEG))
        lat_out[i] = cur_lat
        lon_out[i] = cur_lon

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
            "latitud":                   round(float(lat_out[i]), 6),
            "longitud":                  round(float(lon_out[i]), 6),
            "metros_recorridos":         float(metros[i]),
            "velocidad_movimiento_prom": float(vel[i]),
        }
        for i in range(n)
    ]


# ─────────────────────────────────────────────
# HEALTH ANALYSES
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
# SERVICIO
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

        print("🌱 Seed iniciado — truncando tablas...")
        _truncate_and_reset(self.db)
        print(f"✓ Tablas limpias. Generando {len(RODEO)} vacas...")
        random.seed(RANDOM_SEED)

        cows_created = collars_created = readings_created = analyses_created = 0

        # Paso 1: cows + collars
        cow_collar_map: list[tuple[int, int, str]] = []
        for row_idx, (_, label) in enumerate(RODEO):
            cow = Cow(
                breed=BREEDS[row_idx % len(BREEDS)],
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
            cows_created += 1
            collars_created += 1
            print(f"  [{row_idx + 1}/{len(RODEO)}] Vaca #{cow.id} ({label}) + collar creados")
        self.db.commit()
        print(f"✓ {cows_created} vacas y {collars_created} collares guardados en DB")

        # Paso 2: readings
        print(f"📡 Generando readings ({n} registros por vaca × {len(cow_collar_map)} vacas)...")
        for idx, (cow_id, collar_id, label) in enumerate(cow_collar_map):
            rows = _generate_readings_fast(cow_id, collar_id, label, start, n, now)
            self.db.execute(text("""
                INSERT INTO readings
                    (timestamp, cow_id, collar_id,
                     temperatura_corporal_prom, hubo_rumia,
                     frec_cardiaca_prom, rmssd, sdnn, hubo_vocalizacion,
                     latitud, longitud, metros_recorridos, velocidad_movimiento_prom)
                VALUES
                    (:timestamp, :cow_id, :collar_id,
                     :temperatura_corporal_prom, :hubo_rumia,
                     :frec_cardiaca_prom, :rmssd, :sdnn, :hubo_vocalizacion,
                     :latitud, :longitud, :metros_recorridos, :velocidad_movimiento_prom)
            """), rows)
            readings_created += len(rows)
            print(f"  [{idx + 1}/{len(cow_collar_map)}] Vaca #{cow_id} ({label}) — {len(rows)} readings insertados")
        self.db.commit()
        print(f"✓ {readings_created:,} readings guardados en DB")

        # Paso 3: health analyses
        print(f"🏥 Generando health analyses ({BACK_HEALTH} días × 24hs × {len(RODEO)} vacas)...")
        for seq, (_, label) in enumerate(RODEO):
            cow_id = seq + 1
            rows = _generate_health_analyses(cow_id, label, now)
            self.db.execute(text("""
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
            """), rows)
            analyses_created += len(rows)
            print(f"  [{seq + 1}/{len(RODEO)}] Vaca #{cow_id} ({label}) — {len(rows)} análisis insertados")
        self.db.commit()
        print(f"✓ {analyses_created:,} health analyses guardados en DB")

        return {
            "cows_created":     cows_created,
            "collars_created":  collars_created,
            "readings_created": readings_created,
            "analyses_created": analyses_created,
            "message": (
                f"Seed OK — {cows_created} vacas, {readings_created:,} readings "
                f"({BACK_READINGS}d atrás → {FORWARD_READINGS}d adelante), "
                f"{analyses_created:,} health analyses ({BACK_HEALTH} días)"
            ),
        }