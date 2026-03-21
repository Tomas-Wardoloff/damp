"""
DAMP - Life Stories Generator v3
Labels: sana | subclinica | mastitis | celo | febril | digestivo

Genera datos desde N días atrás hasta N días adelante.
Cada vaca tiene una personalidad dentro de su clase.

Uso:
  python life_stories.py              # 2 días atrás + 4 adelante
  python life_stories.py --back 3 --forward 5
"""

import csv, math, random, argparse
from datetime import datetime, timedelta
from pathlib import Path

IV_MIN     = 5
OUTPUT_DIR = Path("data_simulador")

def circ(h):
    return 0.55 + 0.45*(math.exp(-0.5*((h-7)/1.5)**2)+math.exp(-0.5*((h-17)/1.5)**2))

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def sigmoide(x, centro, pendiente=0.1):
    return 1 / (1 + math.exp(-pendiente * (x - centro)))

# ─────────────────────────────────────────────
# PERSONALIDADES
# Devuelven (temp_m, hr_m, rmssd_m, vel_base, prob_rum_factor, prob_voc_extra)
# prob_rum_factor multiplica la probabilidad base de rumia
# prob_voc_extra  se suma a la probabilidad base de vocalización
# ─────────────────────────────────────────────

# ── SANA ─────────────────────────────────────
def sana_tranquila(i, n, h):
    return 38.5, 62.0, 43.0, 1.2, 1.0, 0.0

def sana_activa(i, n, h):
    c = circ(h)
    return 38.6, 66.0, 41.0, 1.4 + c * 0.8, 1.0, 0.0

def sana_estresada(i, n, h):
    # Estrés ambiental: RMSSD bajo y HR alta pero sin infección
    # Confunde al modelo — parece subclinica pero es sana
    prog   = i / n
    estres = math.sin(math.pi * clamp(prog, 0, 1)) * 0.7
    return 38.7 + estres * 0.3, 68 + estres * 8, 36 - estres * 10, 1.5, 0.9, 0.02

# ── SUBCLINICA ───────────────────────────────
def subclinica_temprana(i, n, h):
    # Recién iniciando — casi normal, leve empeoramiento al final
    prog   = i / n
    avance = sigmoide(prog * n, n * 0.5, 0.03) * 0.25
    return 38.7 + avance * 0.8, 66 + avance * 8, 38 - avance * 10, 1.4 - avance * 0.3, 0.85, 0.03

def subclinica_progresando(i, n, h):
    # Avance visible — empieza limítrofe con sana, termina claramente subclinica
    prog   = i / n
    avance = sigmoide(prog * n, n * 0.3, 0.05) * 0.55
    return 38.8 + avance * 1.2, 67 + avance * 10, 37 - avance * 12, 1.3 - avance * 0.4, 0.75, 0.05

# ── MASTITIS (ex-clínica) ─────────────────────
def mastitis_moderada(i, n, h):
    # Síntomas claros con altibajos durante el día
    prog        = i / n
    fluctuacion = math.sin(2 * math.pi * prog) * 0.15
    base        = clamp(sigmoide(prog * n, n * 0.2, 0.08) * 0.8 + fluctuacion, 0, 1.0)
    # Rumia muy baja — cuarto afectado duele al moverse
    return 38.6 + base * 1.6, 65 + base * 22, 40 - base * 22, 0.9 - base * 0.5, 0.3, 0.15

def mastitis_severa(i, n, h):
    # Síntomas fuertes desde el inicio, empeora durante el día
    prog = i / n
    base = 0.7 + sigmoide(prog * n, n * 0.3, 0.06) * 0.3
    return 38.6 + base * 2.0, 65 + base * 27, 40 - base * 26, 0.6 - base * 0.4, 0.15, 0.22

# ── CELO ─────────────────────────────────────
def celo_activo(i, n, h):
    """
    Vaca en celo: movimiento x3 especialmente de noche (22hs-4hs).
    HR sube, RMSSD normal (no hay inflamación), temperatura normal.
    Vocalización alta. GPS spread se dispara.
    Duración típica: 12-18hs — en el día simulado está en el pico.
    """
    # Actividad muy alta de noche — invertir el ritmo circadiano
    hora_celo = math.exp(-0.5 * ((h - 23) / 3.0) ** 2) + \
                math.exp(-0.5 * ((h - 1)  / 2.0) ** 2)
    factor_noche = 0.4 + 0.6 * hora_celo
    vel_celo = (2.8 + factor_noche * 2.0)   # mucho movimiento
    return 38.7, 72.0, 39.0, vel_celo, 0.8, 0.25

def celo_inicio(i, n, h):
    """
    Inicio del celo — actividad aumentando, más sutil.
    """
    prog   = i / n
    avance = sigmoide(prog * n, n * 0.4, 0.06) * 0.7
    hora_celo = math.exp(-0.5 * ((h - 22) / 3.5) ** 2)
    vel_celo = 1.8 + avance * 1.8 + hora_celo * 1.2
    return 38.6 + avance * 0.1, 68 + avance * 8, 40 - avance * 3, vel_celo, 0.85, 0.12

# ── FEBRIL ────────────────────────────────────
def febril_viral(i, n, h):
    """
    Fiebre sin foco (viral/respiratoria).
    Temp alta como mastitis PERO movimiento casi normal y RMSSD ok.
    La vaca sigue pastoreando — distinguible de mastitis por esta razón.
    """
    prog  = i / n
    pico  = sigmoide(prog * n, n * 0.3, 0.07) * 0.85
    return 38.6 + pico * 1.8, 70 + pico * 12, 36 - pico * 6, 1.3 - pico * 0.3, 0.75, 0.08

def febril_moderado(i, n, h):
    """
    Fiebre moderada — menos severa, más overlap con sana estresada.
    """
    prog = i / n
    pico = sigmoide(prog * n, n * 0.4, 0.05) * 0.55
    return 38.6 + pico * 1.2, 68 + pico * 9, 37 - pico * 5, 1.4 - pico * 0.2, 0.85, 0.05

# ── DIGESTIVO ─────────────────────────────────
def digestivo_acidosis(i, n, h):
    """
    Acidosis ruminal: RUMIA COLAPSA primero (indicador clave).
    Temp levemente alta, HR moderada, movimiento bajo.
    La caída de rumia es lo que distingue digestivo de mastitis.
    """
    prog  = i / n
    avance = sigmoide(prog * n, n * 0.25, 0.08) * 0.8
    # prob_rum_factor muy bajo — el rumen no funciona
    return 38.8 + avance * 0.9, 68 + avance * 14, 35 - avance * 8, 1.0 - avance * 0.5, 0.12, 0.10

def digestivo_timpanismo(i, n, h):
    """
    Timpanismo: rumen inflado. Animal muy quieto por dolor abdominal.
    Vocalización alta, HR elevada, temp normal.
    Movimiento casi cero — más quieto que mastitis clínica incluso.
    """
    prog  = i / n
    avance = sigmoide(prog * n, n * 0.2, 0.10) * 0.9
    return 38.9 + avance * 0.7, 70 + avance * 18, 34 - avance * 10, 0.5 - avance * 0.35, 0.08, 0.28

# ─────────────────────────────────────────────
# RODEO — 30 vacas, 5 por clase
# ─────────────────────────────────────────────
RODEO = [
    # id   label         fn                    personalidad
    (1,  "sana",       sana_tranquila,         "tranquila"),
    (2,  "sana",       sana_activa,            "activa"),
    (3,  "sana",       sana_activa,            "activa"),
    (4,  "sana",       sana_estresada,         "estresada"),
    (5,  "sana",       sana_tranquila,         "tranquila"),

    (6,  "subclinica", subclinica_temprana,    "temprana"),
    (7,  "subclinica", subclinica_progresando, "progresando"),
    (8,  "subclinica", subclinica_temprana,    "temprana"),
    (9,  "subclinica", subclinica_progresando, "progresando"),
    (10, "subclinica", subclinica_temprana,    "temprana"),

    (11, "mastitis",   mastitis_moderada,      "moderada"),
    (12, "mastitis",   mastitis_severa,        "severa"),
    (13, "mastitis",   mastitis_moderada,      "moderada"),
    (14, "mastitis",   mastitis_severa,        "severa"),
    (15, "mastitis",   mastitis_moderada,      "moderada"),

    (16, "celo",       celo_activo,            "activo"),
    (17, "celo",       celo_inicio,            "inicio"),
    (18, "celo",       celo_activo,            "activo"),
    (19, "celo",       celo_inicio,            "inicio"),
    (20, "celo",       celo_activo,            "activo"),

    (21, "febril",     febril_viral,           "viral"),
    (22, "febril",     febril_moderado,        "moderado"),
    (23, "febril",     febril_viral,           "viral"),
    (24, "febril",     febril_moderado,        "moderado"),
    (25, "febril",     febril_viral,           "viral"),

    (26, "digestivo",  digestivo_acidosis,     "acidosis"),
    (27, "digestivo",  digestivo_timpanismo,   "timpanismo"),
    (28, "digestivo",  digestivo_acidosis,     "acidosis"),
    (29, "digestivo",  digestivo_timpanismo,   "timpanismo"),
    (30, "digestivo",  digestivo_acidosis,     "acidosis"),
]

# ─────────────────────────────────────────────
# GENERADOR
# ─────────────────────────────────────────────
def generar_vaca(cow_id, label, fn, personalidad, start, n):
    lat0 = -34.6037 + random.uniform(-0.05, 0.05)
    lon0 = -60.9265 + random.uniform(-0.05, 0.05)
    lat, lon = lat0, lon0
    # Radio GPS más amplio para celo (mucho movimiento)
    radio = {"sana": 0.012, "subclinica": 0.008, "mastitis": 0.005,
             "celo": 0.020, "febril": 0.009, "digestivo": 0.004}.get(label, 0.008)

    gps_freeze     = random.randint(80, 180) if random.random() < 0.25 else -1
    gps_freeze_len = random.randint(5, 12)

    rows = []
    for i in range(n):
        ts  = start + timedelta(minutes=i * IV_MIN)
        h   = ts.hour + ts.minute / 60.0
        c   = circ(h)
        rc  = random.gauss(0, 1)

        temp_m, hr_m, rmssd_m, vel_base, rum_factor, voc_extra = fn(i, n, h)

        # Temperatura
        temp = clamp(random.gauss(temp_m, 0.35) + rc * 0.07, 36.5, 42.5)
        temp = None if random.random() < 0.008 else round(temp, 2)

        # HR — artefacto de movimiento brusco ~1%
        hr = clamp(random.gauss(hr_m, 6.0) + rc * 1.5, 38, 130)
        hr = round(random.uniform(38, 48) if random.random() < 0.010 else hr, 1)

        # HRV
        rmssd = round(max(4.0, random.gauss(max(5.0, rmssd_m), 5.0) - rc * 0.8), 2)
        sdnn  = round(max(rmssd * 1.05, rmssd * random.uniform(1.1, 1.45)), 2)

        # Rumia — modulada por el rum_factor de la personalidad
        prob_rum = clamp((rmssd_m / 40.0) * (0.6 + 0.4 * c) * rum_factor, 0.02, 0.92)
        if random.random() < 0.02:
            prob_rum = min(prob_rum + 0.4, 1.0)   # falso positivo
        hubo_rumia = int(random.random() < prob_rum)

        # Vocalización
        prob_voc   = clamp(0.07 + (temp_m - 38.6) / 2.0 * 0.20 + voc_extra, 0.02, 0.95)
        hubo_vocal = int(random.random() < prob_voc)

        # Velocidad — celo tiene mucho movimiento nocturno
        vel_std = 0.8 if label == "celo" else 0.6
        vel     = round(max(0.0, random.gauss(vel_base * c if label != "celo"
                                              else vel_base, vel_std)), 2)
        metros  = round(vel * (IV_MIN / 60) * 1000, 1)

        # GPS
        if gps_freeze > 0 and gps_freeze <= i < gps_freeze + gps_freeze_len:
            pass
        else:
            paso = (vel / 3600) * IV_MIN * 60 / 111320
            lat  = clamp(lat + random.gauss(0, paso * 0.5), lat0 - radio, lat0 + radio)
            lon  = clamp(lon + random.gauss(0, paso * 0.5), lon0 - radio, lon0 + radio)

        rows.append({
            "label":                      label,
            "label_animal":               label,
            "timestamp":                  ts.strftime("%Y-%m-%d %H:%M:%S"),
            "collar_id":                  f"COW_{cow_id:03d}",
            "progresion":                 round(i / n, 4),
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
# MAIN
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="DAMP Life Stories Generator v3")
    parser.add_argument("--back",    type=int, default=2)
    parser.add_argument("--forward", type=int, default=4)
    args = parser.parse_args()

    now   = datetime.now().replace(second=0, microsecond=0)
    now   = now - timedelta(minutes=now.minute % IV_MIN)
    start = now - timedelta(days=args.back)
    end   = now + timedelta(days=args.forward)
    n     = int((end - start).total_seconds() / 60 // IV_MIN)

    OUTPUT_DIR.mkdir(exist_ok=True)
    random.seed(42)

    labels_str = "sana | subclinica | mastitis | celo | febril | digestivo"
    print("DAMP Life Stories Generator v3")
    print(f"  Labels  : {labels_str}")
    print(f"  Desde   : {start:%Y-%m-%d %H:%M}  ({args.back} días atrás)")
    print(f"  Hasta   : {end:%Y-%m-%d %H:%M}  ({args.forward} días adelante)")
    print(f"  Total   : {args.back+args.forward} días  ({n} reg/vaca)")
    print(f"  Vacas   : {len(RODEO)}  (5 por clase)\n")

    for cow_id, label, fn, personalidad in RODEO:
        rows = generar_vaca(cow_id, label, fn, personalidad, start, n)
        path = OUTPUT_DIR / f"cow_{cow_id:03d}_{label}_{personalidad}.csv"
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows)
        print(f"  ✓ COW_{cow_id:03d}  [{label:>10}]  [{personalidad:>12}]  → {path.name}")

    print(f"\n✓ {len(RODEO) * n:,} registros totales en ./{OUTPUT_DIR}/")
    print(f"\nCron (crontab -e):")
    print(f"  */5 * * * * cd /ruta/damp && python sender.py >> logs/sender.log 2>&1")
    print(f"\nCuando se agoten los {args.forward} días regenerá:")
    print(f"  python life_stories.py --back 0 --forward 7")

if __name__ == "__main__":
    main()