"""
DAMP Seed Service
Reset + recarga de cows, collars, readings y health_analyses.

Vacas: 21 (estado actual exacto)
  - 10 sanas  (vacas 1-10, vaca 3 tuvo fiebre, vaca 4 tuvo mastitis en el historial)
  - 5  celo   (vacas 11-15)
  - 2  mastitis (vacas 16-17)
  - 2  febril  (vacas 18-19)
  - 2  digestivo (vacas 20-21)

Readings:  1 día atrás + 6 días adelante (7 días total)
Health:    7 días atrás, 1 análisis por hora (168 por vaca)
           Las últimas 24hs reflejan el estado actual.
           Vacas 3 y 4 tienen episodios pasados (febril y mastitis resp.)
"""

import math
import random
from datetime import datetime, timedelta

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
IV_MIN          = 5
BACK_READINGS   = 1     # días de readings hacia atrás
FORWARD_READINGS= 6     # días de readings hacia adelante
BACK_HEALTH     = 7     # días de health analyses hacia atrás

RANDOM_SEED = 42

BREEDS = [
    "Holando Argentino",
    "Jersey",
    "Pardo Suizo",
    "Shorthorn Lechero",
    "Ayrshire",
]

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def _circ(h: float) -> float:
    return 0.55 + 0.45 * (
        math.exp(-0.5 * ((h - 7) / 1.5) ** 2) +
        math.exp(-0.5 * ((h - 17) / 1.5) ** 2)
    )

def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

def _sigmoide(x: float, centro: float, pendiente: float = 0.1) -> float:
    return 1 / (1 + math.exp(-pendiente * (x - centro)))


# ─────────────────────────────────────────────
# PERSONALIDADES
# ─────────────────────────────────────────────
def sana_tranquila(i, n, h):
    return 38.5, 62.0, 43.0, 1.2, 1.0, 0.0

def sana_activa(i, n, h):
    return 38.6, 66.0, 41.0, 1.4 + _circ(h) * 0.8, 1.0, 0.0

def sana_estresada(i, n, h):
    prog   = i / n
    estres = math.sin(math.pi * _clamp(prog, 0, 1)) * 0.7
    return 38.7 + estres * 0.3, 68 + estres * 8, 36 - estres * 10, 1.5, 0.9, 0.02

def mastitis_moderada(i, n, h):
    prog        = i / n
    fluctuacion = math.sin(2 * math.pi * prog) * 0.15
    base        = _clamp(_sigmoide(prog * n, n * 0.2, 0.08) * 0.8 + fluctuacion, 0, 1.0)
    return 38.6 + base * 1.6, 65 + base * 22, 40 - base * 22, 0.9 - base * 0.5, 0.3, 0.15

def mastitis_severa(i, n, h):
    prog = i / n
    base = 0.7 + _sigmoide(prog * n, n * 0.3, 0.06) * 0.3
    return 38.6 + base * 2.0, 65 + base * 27, 40 - base * 26, 0.6 - base * 0.4, 0.15, 0.22

def celo_activo(i, n, h):
    hora_celo    = (math.exp(-0.5 * ((h - 23) / 3.0) ** 2) +
                   math.exp(-0.5 * ((h - 1)  / 2.0) ** 2))
    factor_noche = 0.4 + 0.6 * hora_celo
    return 38.7, 72.0, 39.0, 2.8 + factor_noche * 2.0, 0.8, 0.25

def celo_inicio(i, n, h):
    prog      = i / n
    avance    = _sigmoide(prog * n, n * 0.4, 0.06) * 0.7
    hora_celo = math.exp(-0.5 * ((h - 22) / 3.5) ** 2)
    return 38.6 + avance * 0.1, 68 + avance * 8, 40 - avance * 3, 1.8 + avance * 1.8 + hora_celo * 1.2, 0.85, 0.12

def febril_viral(i, n, h):
    prog = i / n
    pico = _sigmoide(prog * n, n * 0.05, 0.06) * 0.85
    return 38.6 + pico * 1.9, 70 + pico * 13, 36 - pico * 7, 1.35 - pico * 0.25, 0.72, 0.09

def febril_moderado(i, n, h):
    prog        = i / n
    pico        = _sigmoide(prog * n, n * 0.08, 0.05) * 0.60
    fluctuacion = math.sin(2 * math.pi * prog * 3) * 0.08
    pico        = _clamp(pico + fluctuacion, 0, 0.7)
    return 38.6 + pico * 1.3, 68 + pico * 10, 37 - pico * 6, 1.4 - pico * 0.2, 0.82, 0.06

def digestivo_acidosis(i, n, h):
    prog   = i / n
    avance = _sigmoide(prog * n, n * 0.25, 0.08) * 0.8
    return 38.8 + avance * 0.9, 68 + avance * 14, 35 - avance * 8, 1.0 - avance * 0.5, 0.12, 0.10

def digestivo_timpanismo(i, n, h):
    prog   = i / n
    avance = _sigmoide(prog * n, n * 0.2, 0.10) * 0.9
    return 38.9 + avance * 0.7, 70 + avance * 18, 34 - avance * 10, 0.5 - avance * 0.35, 0.08, 0.28


# ─────────────────────────────────────────────
# RODEO — 21 vacas
# Estado actual exacto: 10 sana, 5 celo, 2 mastitis, 2 febril, 2 digestivo
# cow_id 3 → historial de FEBRIL hace ~4 días
# cow_id 4 → historial de MASTITIS hace ~5 días
# ─────────────────────────────────────────────
RODEO = [
    # id   label         fn                 personalidad
    (1,  "sana",       sana_tranquila,    "tranquila"),
    (2,  "sana",       sana_activa,       "activa"),
    (3,  "sana",       sana_tranquila,    "tranquila"),   # ex-febril
    (4,  "sana",       sana_activa,       "activa"),      # ex-mastitis
    (5,  "sana",       sana_tranquila,    "tranquila"),
    (6,  "sana",       sana_activa,       "activa"),
    (7,  "sana",       sana_estresada,    "estresada"),
    (8,  "sana",       sana_tranquila,    "tranquila"),
    (9,  "sana",       sana_activa,       "activa"),
    (10, "sana",       sana_tranquila,    "tranquila"),
    (11, "celo",       celo_activo,       "activo"),
    (12, "celo",       celo_inicio,       "inicio"),
    (13, "celo",       celo_activo,       "activo"),
    (14, "celo",       celo_inicio,       "inicio"),
    (15, "celo",       celo_activo,       "activo"),
    (16, "mastitis",   mastitis_moderada, "moderada"),
    (17, "mastitis",   mastitis_severa,   "severa"),
    (18, "febril",     febril_viral,      "viral"),
    (19, "febril",     febril_moderado,   "moderado"),
    (20, "digestivo",  digestivo_acidosis,   "acidosis"),
    (21, "digestivo",  digestivo_timpanismo, "timpanismo"),
]

# ─────────────────────────────────────────────
# MAPEO LABEL → HealthStatus
# ─────────────────────────────────────────────
_LABEL_TO_STATUS: dict[str, HealthStatus] = {
    "sana":       HealthStatus.SANA,
    "mastitis":   HealthStatus.MASTITIS,
    "celo":       HealthStatus.CELO,
    "febril":     HealthStatus.FEBRIL,
    "digestivo":  HealthStatus.DIGESTIVO,
}

_SECONDARY_MAP: dict[str, HealthStatus] = {
    "sana":       HealthStatus.FEBRIL,
    "mastitis":   HealthStatus.FEBRIL,
    "celo":       HealthStatus.SANA,
    "febril":     HealthStatus.MASTITIS,
    "digestivo":  HealthStatus.MASTITIS,
}


# ─────────────────────────────────────────────
# GENERADOR DE READINGS
# ─────────────────────────────────────────────
def _generate_readings(cow_id, collar_id, label, fn, start, n) -> list[dict]:
    random.seed(RANDOM_SEED + cow_id)

    lat0 = -34.6037 + random.uniform(-0.05, 0.05)
    lon0 = -60.9265 + random.uniform(-0.05, 0.05)
    lat, lon = lat0, lon0

    radio = {
        "sana": 0.012, "mastitis": 0.005,
        "celo": 0.020, "febril": 0.009, "digestivo": 0.004,
    }.get(label, 0.008)

    gps_freeze     = random.randint(80, 180) if random.random() < 0.25 else -1
    gps_freeze_len = random.randint(5, 12)

    rows = []
    for i in range(n):
        ts  = start + timedelta(minutes=i * IV_MIN)
        h   = ts.hour + ts.minute / 60.0
        c   = _circ(h)
        rc  = random.gauss(0, 1)

        temp_m, hr_m, rmssd_m, vel_base, rum_factor, voc_extra = fn(i, n, h)

        micro_temp = micro_hr = micro_rmssd = 0.0
        if random.random() < 0.04:
            evento = random.choice(["temp_spike", "hr_spike", "rmssd_drop", "rmssd_up"])
            if evento == "temp_spike":   micro_temp  =  random.uniform(0.3, 0.8)
            elif evento == "hr_spike":   micro_hr    =  random.uniform(5, 15)
            elif evento == "rmssd_drop": micro_rmssd = -random.uniform(5, 12)
            elif evento == "rmssd_up":   micro_rmssd =  random.uniform(4, 10)

        temp_val = _clamp(random.gauss(temp_m, 0.45) + rc * 0.08 + micro_temp, 36.5, 42.5)
        temp     = round(temp_val if random.random() >= 0.008 else 38.6, 2)

        hr_raw = _clamp(random.gauss(hr_m, 7.0) + rc * 1.5 + micro_hr, 38, 130)
        hr     = round(random.uniform(38, 48) if random.random() < 0.010 else hr_raw, 1)

        rmssd = round(max(4.0, random.gauss(max(5.0, rmssd_m), 6.5) - rc * 0.8 + micro_rmssd), 2)
        sdnn  = round(max(rmssd * 1.05, rmssd * random.uniform(1.1, 1.45)), 2)

        prob_rum  = _clamp((rmssd_m / 40.0) * (0.6 + 0.4 * c) * rum_factor, 0.02, 0.92)
        if random.random() < 0.02:
            prob_rum = min(prob_rum + 0.4, 1.0)
        hubo_rumia = random.random() < prob_rum

        prob_voc   = _clamp(0.07 + (temp_m - 38.6) / 2.0 * 0.20 + voc_extra, 0.02, 0.95)
        hubo_vocal = random.random() < prob_voc

        vel_std      = 0.8 if label == "celo" else 0.6
        vel_base_adj = vel_base if label == "celo" else vel_base * c
        vel          = round(max(0.0, random.gauss(vel_base_adj, vel_std)), 2)
        metros       = round(vel * (IV_MIN / 60) * 1000, 1)

        if not (gps_freeze > 0 and gps_freeze <= i < gps_freeze + gps_freeze_len):
            paso = (vel / 3600) * IV_MIN * 60 / 111320
            lat  = _clamp(lat + random.gauss(0, paso * 0.5), lat0 - radio, lat0 + radio)
            lon  = _clamp(lon + random.gauss(0, paso * 0.5), lon0 - radio, lon0 + radio)

        rows.append({
            "timestamp":                 ts,
            "cow_id":                    cow_id,
            "collar_id":                 collar_id,
            "temperatura_corporal_prom": temp,
            "hubo_rumia":                hubo_rumia,
            "frec_cardiaca_prom":        hr,
            "rmssd":                     rmssd,
            "sdnn":                      sdnn,
            "hubo_vocalizacion":         hubo_vocal,
            "latitud":                   round(lat, 6),
            "longitud":                  round(lon, 6),
            "metros_recorridos":         metros,
            "velocidad_movimiento_prom": vel,
        })
    return rows


# ─────────────────────────────────────────────
# GENERADOR DE HEALTH ANALYSES
# 7 días para atrás, 1 por hora = 168 análisis por vaca
#
# Lógica de historial por vaca:
#   - cow_id 3 (sana, ex-febril):
#       días 7-5 atrás → SANA
#       días 5-3 atrás → FEBRIL (el episodio)
#       días 3-0       → SANA (recuperada)
#   - cow_id 4 (sana, ex-mastitis):
#       días 7-6 atrás → SANA
#       días 6-4 atrás → MASTITIS (el episodio)
#       días 4-0       → SANA (recuperada)
#   - resto: su label actual durante toda la semana
# ─────────────────────────────────────────────
def _status_for_hour(cow_id: int, label: str, hours_ago: int) -> HealthStatus:
    """Devuelve el HealthStatus que corresponde a esa hora del historial."""

    # Vaca 3: tuvo fiebre entre hace 5 y 3 días (120hs - 72hs atrás)
    if cow_id == 3:
        if 72 < hours_ago <= 120:
            return HealthStatus.FEBRIL
        return HealthStatus.SANA

    # Vaca 4: tuvo mastitis entre hace 6 y 4 días (144hs - 96hs atrás)
    if cow_id == 4:
        if 96 < hours_ago <= 144:
            return HealthStatus.MASTITIS
        return HealthStatus.SANA

    return _LABEL_TO_STATUS.get(label, HealthStatus.SANA)


def _secondary_for_status(status: HealthStatus) -> HealthStatus:
    return {
        HealthStatus.SANA:       HealthStatus.FEBRIL,
        HealthStatus.MASTITIS:   HealthStatus.FEBRIL,
        HealthStatus.CELO:       HealthStatus.SANA,
        HealthStatus.FEBRIL:     HealthStatus.MASTITIS,
        HealthStatus.DIGESTIVO:  HealthStatus.MASTITIS,
    }.get(status, HealthStatus.SANA)


def _mock_confidences(rng: random.Random) -> tuple[float, float]:
    primary = round(rng.uniform(0.55, 0.92), 4)
    residuo = round(rng.uniform(0.01, 0.08), 4)
    secondary = max(0.01, round(1.0 - primary - residuo, 4))
    return primary, secondary


def _generate_health_analyses(cow_id: int, label: str, now: datetime) -> list[dict]:
    rng = random.Random(cow_id * 999)

    rows = []
    # hours_ago va de BACK_HEALTH*24 hasta 1 (más viejo → más reciente)
    for hours_ago in range(BACK_HEALTH * 24, 0, -1):
        created_at     = now - timedelta(hours=hours_ago)
        primary_status = _status_for_hour(cow_id, label, hours_ago)
        secondary_status = _secondary_for_status(primary_status)
        primary_conf, secondary_conf = _mock_confidences(rng)

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
            "created_at":           created_at,
        })
    return rows


# ─────────────────────────────────────────────
# RESET FK-SAFE
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

        # ── Paso 1: cows + collars + readings ──────────────────
        for row_idx, (cow_num, label, fn, _p) in enumerate(RODEO):
            cow = Cow(
                breed=BREEDS[row_idx % len(BREEDS)],
                registration_date=datetime.utcnow(),
                age_months=random.randint(18, 84),
            )
            self.db.add(cow)
            self.db.flush()
            cows_created += 1

            collar = Collar(
                assigned_cow_id=cow.id,
                assigned_at=datetime.utcnow(),
                unassigned_at=None,
            )
            self.db.add(collar)
            self.db.flush()
            collars_created += 1

            reading_rows = _generate_readings(
                cow_id=cow.id,
                collar_id=collar.id,
                label=label,
                fn=fn,
                start=start,
                n=n,
            )
            BATCH = 500
            for b in range(0, len(reading_rows), BATCH):
                self.db.bulk_insert_mappings(Reading, reading_rows[b:b + BATCH])
            readings_created += len(reading_rows)

        self.db.commit()

        # ── Paso 2: health analyses ─────────────────────────────
        # Los cow_ids son 1..21 garantizados por el RESTART IDENTITY
        for seq, (_cow_num, label, _fn, _p) in enumerate(RODEO):
            cow_id = seq + 1
            analysis_rows = _generate_health_analyses(
                cow_id=cow_id,
                label=label,
                now=now,
            )
            BATCH = 100
            for b in range(0, len(analysis_rows), BATCH):
                self.db.bulk_insert_mappings(HealthAnalysis, analysis_rows[b:b + BATCH])
            analyses_created += len(analysis_rows)

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
                f"({BACK_HEALTH} días atrás, 1/hora)"
            ),
        }