"""
DAMP Seed Service — versión optimizada
Usa numpy vectorizado para generación y execute() nativo para inserts.
Tiempo esperado: < 5 segundos para 21 vacas × 7 días.
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
BACK_READINGS    = 7
FORWARD_READINGS = 1
BACK_HEALTH      = 7
RANDOM_SEED      = 42

BREEDS = ["Holando Argentino", "Jersey", "Pardo Suizo", "Shorthorn Lechero", "Ayrshire"]

# ─────────────────────────────────────────────
# PARÁMETROS FISIOLÓGICOS POR ESTADO
# (temp_m, temp_s, hr_m, hr_s, rmssd_m, rmssd_s, vel_m, vel_s, p_rum, p_voc)
# ─────────────────────────────────────────────
_PARAMS = {
    "sana":       (38.55, 0.45,  63.0, 7.0,  41.0, 6.5,  1.5, 0.7,  0.58, 0.07),
    "mastitis":   (40.20, 0.65,  87.0, 9.0,  18.0, 6.0,  0.6, 0.4,  0.12, 0.20),
    "celo":       (38.70, 0.45,  72.0, 7.5,  39.0, 6.5,  4.5, 1.2,  0.55, 0.25),
    "febril":     (39.90, 0.55,  76.0, 8.0,  33.0, 6.5,  1.2, 0.6,  0.45, 0.10),
    "digestivo":  (39.20, 0.55,  78.0, 8.5,  28.0, 6.5,  0.7, 0.4,  0.10, 0.18),
}

# ─────────────────────────────────────────────
# RODEO — 21 vacas
# ─────────────────────────────────────────────
RODEO = [
    (1,  "sana",      "Holstein"),
    (2,  "sana",      "Jersey"),
    (3,  "sana",      "Holstein"),   # ex-febril
    (4,  "sana",      "Jersey"),       # ex-mastitis
    (5,  "sana",      "Holstein"),
    (6,  "sana",      "Jersey"),
    (7,  "sana",      "Holstein"),
    (8,  "sana",      "Jersey"),
    (9,  "sana",      "Holstein"),
    (10, "sana",      "Jersey"),
    (11, "celo",      "Holstein"),
    (12, "celo",      "Jersey"),
    (13, "celo",      "Holstein"),
    (14, "celo",      "Jersey"),
    (15, "celo",      "Holstein"),
    (16, "mastitis",  "Jersey"),
    (17, "mastitis",  "Holstein"),
    (18, "febril",    "Jersey"),
    (19, "febril",    "Holstein"),
    (20, "digestivo", "Jersey"),
    (21, "digestivo", "Holstein"),
]

# ─────────────────────────────────────────────
# HISTORIAL POR VACA
# (label, desde_hours_ago, hasta_hours_ago)
# ─────────────────────────────────────────────
_HISTORIAL: dict[int, list[tuple[str, int, int]]] = {
    1:  [("sana", 168, 0)],
    2:  [("sana", 168, 0)],
    3:  [("sana", 168, 120), ("febril", 120, 72), ("sana", 72, 0)],
    4:  [("sana", 168, 144), ("mastitis", 144, 96), ("sana", 96, 0)],
    5:  [("sana", 168, 0)],
    6:  [("sana", 168, 0)],
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


# ─────────────────────────────────────────────
# GENERADOR VECTORIZADO DE READINGS
# Genera todos los ticks de una vaca de golpe con numpy
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
    hours_ago  = np.array([(now - ts).total_seconds() / 3600 for ts in timestamps])

    # Factor circadiano vectorizado
    circ = 0.55 + 0.45 * (
        np.exp(-0.5 * ((hours_f - 7.0) / 1.5) ** 2) +
        np.exp(-0.5 * ((hours_f - 17.0) / 1.5) ** 2)
    )

    # Label fisiológico por tick — lookup vectorizado
    tick_labels = np.array([_label_at_hours_ago(cow_id, h) for h in hours_ago])

    # Parámetros base por tick — extraer arrays
    p_matrix = np.array([_PARAMS[l] for l in tick_labels])
    temp_m  = p_matrix[:, 0];  temp_s  = p_matrix[:, 1]
    hr_m    = p_matrix[:, 2];  hr_s    = p_matrix[:, 3]
    rmssd_m = p_matrix[:, 4];  rmssd_s = p_matrix[:, 5]
    vel_m   = p_matrix[:, 6];  vel_s   = p_matrix[:, 7]
    p_rum   = p_matrix[:, 8];  p_voc   = p_matrix[:, 9]

    # Ruido correlacionado entre sensores
    rc = rng.standard_normal(n)

    # Micro-eventos cross-class (~4%)
    micro_mask  = rng.random(n) < 0.04
    micro_type  = rng.integers(0, 4, n)   # 0=temp, 1=hr, 2=rmssd_drop, 3=rmssd_up
    micro_vals  = rng.uniform(0.3, 1.1, n)
    micro_temp  = np.where(micro_mask & (micro_type == 0), micro_vals * 0.8, 0.0)
    micro_hr    = np.where(micro_mask & (micro_type == 1), micro_vals * 12, 0.0)
    micro_rmssd = np.where(micro_mask & (micro_type == 2), -micro_vals * 10, 0.0)
    micro_rmssd+= np.where(micro_mask & (micro_type == 3),  micro_vals * 8,  0.0)

    # Temperatura
    temp_circ = 0.1 * np.sin(2 * np.pi * (hours_f - 6) / 24)
    temp_raw  = rng.normal(temp_m, temp_s) + temp_circ + rc * 0.08 + micro_temp
    temp      = np.clip(temp_raw, 36.5, 42.5).round(2)
    # ~0.8% fallas de sensor → usar fallback
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
    fn_night  = np.exp(-0.5 * (np.minimum(np.abs(hours_f - 2),
                                           np.abs(hours_f - 2 + 24)) / 2.5) ** 2)
    prob_rum_adj = np.clip(
        (rmssd_m / 40.0) * (0.5 + 0.5 * circ + fn_night * 0.5) * p_rum,
        0.02, 0.95
    )
    hubo_rumia = (rng.random(n) < prob_rum_adj).astype(bool)

    # Vocalización
    prob_voc_adj = np.clip(0.07 + (temp_m - 38.6) / 2.0 * 0.20 + p_voc, 0.02, 0.95)
    hubo_vocal   = (rng.random(n) < prob_voc_adj).astype(bool)

    # Velocidad — celo tiene movimiento nocturno especial
    is_celo  = (tick_labels == "celo")
    vel_base = np.where(is_celo, vel_m, vel_m * circ)
    vel_std2 = np.where(is_celo, 1.2, vel_s)
    vel      = np.maximum(0.0, rng.normal(vel_base, vel_std2)).round(2)
    
    # Lógica de metros recorridos: no más de 90m (no celo), más de 150m (celo)
    # 90 metros / 5 min = 1.08 km/h (0.3 m/s)
    # 150 metros / 5 min = 1.8 km/h (0.5 m/s)
    metros   = (vel * (IV_MIN * 60)).round(1)
    # Ajuste fino para cumplir con requisitos de metros
    metros   = np.where(is_celo, np.maximum(151.0, metros), np.minimum(89.0, metros))
    # Recalcular velocidad para que sea consistente con metros
    vel      = (metros / (IV_MIN * 60)).round(2)

    # GPS — random walk alrededor de -34.591966, -60.887503
    lat0 = -34.591966
    lon0 = -60.887503
    # 300 metros aprox 0.0027 grados
    radio = 0.0027 
    
    # Cada vaca tiene un offset inicial único pero cercano para que no estén todas en el mismo punto exacto
    cow_offset_lat = rng.uniform(-0.001, 0.001)
    cow_offset_lon = rng.uniform(-0.001, 0.001)
    cur_lat = lat0 + cow_offset_lat
    cur_lon = lon0 + cow_offset_lon

    lat = np.full(n, cur_lat)
    lon = np.full(n, cur_lon)
    
    for i in range(n):
        # El paso se calcula basado en los metros reales generados
        # 111320 metros es aprox 1 grado de latitud
        paso_total = metros[i] / 111320.0
        
        # Dirección aleatoria pero con cierta inercia para que el movimiento se vea natural
        angle = rng.uniform(0, 2 * np.pi)
        d_lat = paso_total * np.cos(angle)
        d_lon = paso_total * np.sin(angle) / np.cos(np.radians(lat0))
        
        new_lat = cur_lat + d_lat
        new_lon = cur_lon + d_lon
        
        # Mantener dentro del radio de 300m (clipping suave)
        if abs(new_lat - lat0) > radio:
            new_lat = lat0 + np.sign(new_lat - lat0) * radio
        if abs(new_lon - lon0) > radio:
            new_lon = lon0 + np.sign(new_lon - lon0) * radio
            
        cur_lat, cur_lon = new_lat, new_lon
        lat[i] = cur_lat
        lon[i] = cur_lon

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
            "latitud":                   round(float(lat[i]), 6),
            "longitud":                  round(float(lon[i]), 6),
            "metros_recorridos":         float(metros[i]),
            "velocidad_movimiento_prom": float(vel[i]),
        }
        for i in range(n)
    ]


# ─────────────────────────────────────────────
# GENERADOR DE HEALTH ANALYSES — ya era rápido, se mantiene igual
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

        # ── Paso 1: cows + collars (sin readings aún) ──────────
        cow_collar_map: list[tuple[int, int, str]] = []   # (cow_id, collar_id, label)
        for row_idx, (cow_num, label, cow_name) in enumerate(RODEO):
            cow = Cow(
                name=cow_name,
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
            cows_created    += 1
            collars_created += 1

        self.db.commit()   # commit cows y collars juntos

        # ── Paso 2: readings — insert nativo por vaca ──────────
        for cow_id, collar_id, label in cow_collar_map:
            rows = _generate_readings_fast(
                cow_id=cow_id, collar_id=collar_id,
                label=label, start=start, n=n, now=now,
            )
            # INSERT nativo en un solo execute — mucho más rápido que ORM
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
        for seq, (_cow_num, label, _cow_name) in enumerate(RODEO):
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