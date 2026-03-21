"""
DAMP Seed Service
Porta la lógica de life_stories.py directo a la base de datos.
Reset + recarga de cows, collars y readings en una sola llamada.

Clases: sana | mastitis | celo | febril | digestivo  (subclinica removida)
Vacas:  30 (5 por clase) — misma distribución que life_stories
"""

import math
import random
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.collar.models import Collar
from app.modules.cow.models import Cow
from app.modules.reading.models import Reading

# ─────────────────────────────────────────────
# CONFIG — igual que life_stories.py
# ─────────────────────────────────────────────
IV_MIN   = 5
BACK     = 2    # días hacia atrás
FORWARD  = 4    # días hacia adelante

RANDOM_SEED = 42

BREEDS = [
    "Holando Argentino",
    "Jersey",
    "Pardo Suizo",
    "Shorthorn Lechero",
    "Ayrshire",
]


# ─────────────────────────────────────────────
# HELPERS — copiados de life_stories.py
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
# PERSONALIDADES — mismas funciones que life_stories.py
# (temp_m, hr_m, rmssd_m, vel_base, rum_factor, voc_extra)
# ─────────────────────────────────────────────
def sana_tranquila(i, n, h):
    return 38.5, 62.0, 43.0, 1.2, 1.0, 0.0

def sana_activa(i, n, h):
    c = _circ(h)
    return 38.6, 66.0, 41.0, 1.4 + c * 0.8, 1.0, 0.0

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
# RODEO — 30 vacas, misma distribución que life_stories.py
# ─────────────────────────────────────────────
RODEO = [
    (1,  "sana",       sana_tranquila,    "tranquila"),
    (2,  "sana",       sana_activa,       "activa"),
    (3,  "sana",       sana_activa,       "activa"),
    (4,  "sana",       sana_estresada,    "estresada"),
    (5,  "sana",       sana_tranquila,    "tranquila"),

    (6,  "mastitis",   mastitis_moderada, "moderada"),
    (7,  "mastitis",   mastitis_severa,   "severa"),
    (8,  "mastitis",   mastitis_moderada, "moderada"),
    (9,  "mastitis",   mastitis_severa,   "severa"),
    (10, "mastitis",   mastitis_moderada, "moderada"),

    (11, "celo",       celo_activo,       "activo"),
    (12, "celo",       celo_inicio,       "inicio"),
    (13, "celo",       celo_activo,       "activo"),
    (14, "celo",       celo_inicio,       "inicio"),
    (15, "celo",       celo_activo,       "activo"),

    (16, "febril",     febril_viral,      "viral"),
    (17, "febril",     febril_moderado,   "moderado"),
    (18, "febril",     febril_viral,      "viral"),
    (19, "febril",     febril_moderado,   "moderado"),
    (20, "febril",     febril_viral,      "viral"),

    (21, "digestivo",  digestivo_acidosis,   "acidosis"),
    (22, "digestivo",  digestivo_timpanismo, "timpanismo"),
    (23, "digestivo",  digestivo_acidosis,   "acidosis"),
    (24, "digestivo",  digestivo_timpanismo, "timpanismo"),
    (25, "digestivo",  digestivo_acidosis,   "acidosis"),
]


# ─────────────────────────────────────────────
# GENERADOR DE READINGS — porta generar_vaca de life_stories.py
# ─────────────────────────────────────────────
def _generate_readings(
    cow_id: int,
    collar_id: int,
    label: str,
    fn,
    start: datetime,
    n: int,
) -> list[dict]:
    random.seed(RANDOM_SEED + cow_id)   # seed por vaca para reproducibilidad

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

        # Micro-eventos cross-class (~4%)
        micro_temp = micro_hr = micro_rmssd = 0.0
        if random.random() < 0.04:
            evento = random.choice(["temp_spike", "hr_spike", "rmssd_drop", "rmssd_up"])
            if evento == "temp_spike":   micro_temp  =  random.uniform(0.3, 0.8)
            elif evento == "hr_spike":   micro_hr    =  random.uniform(5, 15)
            elif evento == "rmssd_drop": micro_rmssd = -random.uniform(5, 12)
            elif evento == "rmssd_up":   micro_rmssd =  random.uniform(4, 10)

        # Temperatura — None si falla el sensor (~0.8%)
        temp_val = _clamp(random.gauss(temp_m, 0.45) + rc * 0.08 + micro_temp, 36.5, 42.5)
        temp = None if random.random() < 0.008 else round(temp_val, 2)

        # HR
        hr_raw = _clamp(random.gauss(hr_m, 7.0) + rc * 1.5 + micro_hr, 38, 130)
        hr = round(random.uniform(38, 48) if random.random() < 0.010 else hr_raw, 1)

        # HRV
        rmssd = round(max(4.0, random.gauss(max(5.0, rmssd_m), 6.5) - rc * 0.8 + micro_rmssd), 2)
        sdnn  = round(max(rmssd * 1.05, rmssd * random.uniform(1.1, 1.45)), 2)

        # Rumia
        prob_rum  = _clamp((rmssd_m / 40.0) * (0.6 + 0.4 * c) * rum_factor, 0.02, 0.92)
        if random.random() < 0.02:
            prob_rum = min(prob_rum + 0.4, 1.0)
        hubo_rumia = random.random() < prob_rum

        # Vocalización
        prob_voc   = _clamp(0.07 + (temp_m - 38.6) / 2.0 * 0.20 + voc_extra, 0.02, 0.95)
        hubo_vocal = random.random() < prob_voc

        # Velocidad
        vel_std = 0.8 if label == "celo" else 0.6
        vel_base_adj = vel_base if label == "celo" else vel_base * c
        vel    = round(max(0.0, random.gauss(vel_base_adj, vel_std)), 2)
        metros = round(vel * (IV_MIN / 60) * 1000, 1)

        # GPS
        if gps_freeze > 0 and gps_freeze <= i < gps_freeze + gps_freeze_len:
            pass
        else:
            paso = (vel / 3600) * IV_MIN * 60 / 111320
            lat  = _clamp(lat + random.gauss(0, paso * 0.5), lat0 - radio, lat0 + radio)
            lon  = _clamp(lon + random.gauss(0, paso * 0.5), lon0 - radio, lon0 + radio)

        rows.append({
            "timestamp":                 ts,
            "cow_id":                    cow_id,
            "collar_id":                 collar_id,
            "temperatura_corporal_prom": temp if temp is not None else 38.6,  # fallback si sensor falló
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
# RESET HELPERS
# ─────────────────────────────────────────────
def _reset_sequence(db: Session, table: str, column: str = "id") -> None:
    """Resetea el autoincremental de una tabla a 1."""
    db.execute(text(f"ALTER SEQUENCE {table}_{column}_seq RESTART WITH 1"))


def _truncate_and_reset(db: Session) -> None:
    """Borra todos los registros y resetea secuencias. Orden FK-safe."""
    db.execute(text("TRUNCATE TABLE readings RESTART IDENTITY CASCADE"))
    db.execute(text("TRUNCATE TABLE health_analyses RESTART IDENTITY CASCADE"))
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
        start = now - timedelta(days=BACK)
        end   = now + timedelta(days=FORWARD)
        n     = int((end - start).total_seconds() / 60 // IV_MIN)

        # 1. Reset completo en orden correcto (FK-safe)
        _truncate_and_reset(self.db)

        random.seed(RANDOM_SEED)

        cows_created    = 0
        collars_created = 0
        readings_created = 0

        for row_idx, (cow_num, label, fn, _personalidad) in enumerate(RODEO):
            # ── Crear vaca ────────────────────────────────────
            breed = BREEDS[row_idx % len(BREEDS)]
            cow = Cow(
                breed=breed,
                registration_date=datetime.utcnow(),
                age_months=random.randint(18, 84),  # 1.5 a 7 años
            )
            self.db.add(cow)
            self.db.flush()   # obtiene el id sin commitear aún
            cows_created += 1

            # ── Crear collar asignado a esa vaca ──────────────
            collar = Collar(
                assigned_cow_id=cow.id,
                assigned_at=datetime.utcnow(),
                unassigned_at=None,
            )
            self.db.add(collar)
            self.db.flush()
            collars_created += 1

            # ── Generar y bulk-insert readings ────────────────
            reading_rows = _generate_readings(
                cow_id=cow.id,
                collar_id=collar.id,
                label=label,
                fn=fn,
                start=start,
                n=n,
            )

            # Bulk insert en lotes de 500 para no saturar memoria
            BATCH = 500
            for batch_start in range(0, len(reading_rows), BATCH):
                batch = reading_rows[batch_start : batch_start + BATCH]
                self.db.bulk_insert_mappings(Reading, batch)

            readings_created += len(reading_rows)

        self.db.commit()

        return {
            "cows_created":    cows_created,
            "collars_created": collars_created,
            "readings_created": readings_created,
            "message": (
                f"Seed completado: {cows_created} vacas, "
                f"{collars_created} collares, "
                f"{readings_created:,} readings "
                f"({BACK} días atrás → {FORWARD} días adelante)"
            ),
        }