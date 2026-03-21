"""
DAMP - Life Stories Generator v2
Labels válidos: sana | subclinica | clinica

Genera datos desde 2 días atrás hasta 4 días adelante (6 días total).
Cada vaca tiene una personalidad dentro de su clase.

Uso:
  python life_stories.py              # 2 días atrás + 4 adelante desde hoy
  python life_stories.py --back 3 --forward 5   # personalizado
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
# ─────────────────────────────────────────────
def sana_tranquila(i, n, h):
    return 38.5, 62.0, 43.0, 1.2

def sana_activa(i, n, h):
    c = circ(h)
    return 38.6, 66.0, 41.0, 1.4 + c * 0.8

def sana_estresada(i, n, h):
    prog   = i / n
    estres = math.sin(math.pi * clamp(prog, 0, 1)) * 0.7
    return 38.7 + estres * 0.3, 68 + estres * 8, 36 - estres * 10, 1.5

def subclinica_temprana(i, n, h):
    prog   = i / n
    avance = sigmoide(prog * n, n * 0.5, 0.03) * 0.25
    return 38.7 + avance * 0.8, 66 + avance * 8, 38 - avance * 10, 1.4 - avance * 0.3

def subclinica_progresando(i, n, h):
    prog   = i / n
    avance = sigmoide(prog * n, n * 0.3, 0.05) * 0.55
    return 38.8 + avance * 1.2, 67 + avance * 10, 37 - avance * 12, 1.3 - avance * 0.4

def clinica_moderada(i, n, h):
    prog        = i / n
    fluctuacion = math.sin(2 * math.pi * prog) * 0.15
    base        = clamp(sigmoide(prog * n, n * 0.2, 0.08) * 0.8 + fluctuacion, 0, 1.0)
    return 38.6 + base * 1.6, 65 + base * 22, 40 - base * 22, 0.9 - base * 0.5

def clinica_severa(i, n, h):
    prog = i / n
    base = 0.7 + sigmoide(prog * n, n * 0.3, 0.06) * 0.3
    return 38.6 + base * 2.0, 65 + base * 27, 40 - base * 26, 0.6 - base * 0.4

# ─────────────────────────────────────────────
# RODEO
# ─────────────────────────────────────────────
RODEO = [
    (1,  "sana",       sana_tranquila,         "tranquila"),
    (2,  "sana",       sana_tranquila,         "tranquila"),
    (3,  "sana",       sana_activa,            "activa"),
    (4,  "sana",       sana_activa,            "activa"),
    (5,  "sana",       sana_activa,            "activa"),
    (6,  "sana",       sana_tranquila,         "tranquila"),
    (7,  "sana",       sana_estresada,         "estresada"),
    (8,  "sana",       sana_estresada,         "estresada"),
    (9,  "sana",       sana_activa,            "activa"),
    (10, "sana",       sana_tranquila,         "tranquila"),
    (11, "subclinica", subclinica_temprana,    "temprana"),
    (12, "subclinica", subclinica_temprana,    "temprana"),
    (13, "subclinica", subclinica_progresando, "progresando"),
    (14, "subclinica", subclinica_progresando, "progresando"),
    (15, "subclinica", subclinica_temprana,    "temprana"),
    (16, "clinica",    clinica_moderada,       "moderada"),
    (17, "clinica",    clinica_moderada,       "moderada"),
    (18, "clinica",    clinica_severa,         "severa"),
    (19, "clinica",    clinica_severa,         "severa"),
    (20, "clinica",    clinica_moderada,       "moderada"),
]

# ─────────────────────────────────────────────
# GENERADOR
# ─────────────────────────────────────────────
def generar_vaca(cow_id, label, fn, personalidad, start, n):
    lat0 = -34.6037 + random.uniform(-0.05, 0.05)
    lon0 = -60.9265 + random.uniform(-0.05, 0.05)
    lat, lon = lat0, lon0
    radio = 0.010 if label == "sana" else 0.006

    gps_freeze     = random.randint(80, 180) if random.random() < 0.3 else -1
    gps_freeze_len = random.randint(5, 15)

    rows = []
    for i in range(n):
        ts  = start + timedelta(minutes=i * IV_MIN)
        h   = ts.hour + ts.minute / 60.0
        c   = circ(h)
        rc  = random.gauss(0, 1)

        temp_m, hr_m, rmssd_m, vel_base = fn(i, n, h)

        # Temperatura
        temp = clamp(random.gauss(temp_m, 0.35) + rc * 0.07, 36.5, 42.5)
        if random.random() < 0.008:
            temp = None
        else:
            temp = round(temp, 2)

        # HR
        hr = round(clamp(random.gauss(hr_m, 6.0) + rc * 1.5, 38, 130), 1)

        # HRV
        rmssd = round(max(4.0, random.gauss(max(5.0, rmssd_m), 5.0) - rc * 0.8), 2)
        sdnn  = round(max(rmssd * 1.05, rmssd * random.uniform(1.1, 1.45)), 2)

        # Rumia
        prob_rum = clamp((rmssd_m / 40.0) * (0.6 + 0.4 * c), 0.05, 0.90)
        if random.random() < 0.02:
            prob_rum = min(prob_rum + 0.5, 1.0)
        hubo_rumia = int(random.random() < prob_rum)

        # Vocalización
        prob_voc   = 0.07 + clamp((temp_m - 38.6) / 2.0, 0, 1) * 0.25
        hubo_vocal = int(random.random() < prob_voc)

        # Velocidad y GPS
        vel    = round(max(0.0, random.gauss(vel_base * c, 0.6)), 2)
        metros = round(vel * (IV_MIN / 60) * 1000, 1)

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
    parser = argparse.ArgumentParser(description="DAMP Life Stories Generator v2")
    parser.add_argument("--back",    type=int, default=2,
                        help="Días hacia atrás desde hoy (default: 2)")
    parser.add_argument("--forward", type=int, default=4,
                        help="Días hacia adelante desde hoy (default: 4)")
    args = parser.parse_args()

    # Inicio = hoy - back días, redondeado al múltiplo de 5 min
    now   = datetime.now().replace(second=0, microsecond=0)
    now   = now - timedelta(minutes=now.minute % IV_MIN)
    start = now - timedelta(days=args.back)
    end   = now + timedelta(days=args.forward)

    n_total = int((end - start).total_seconds() / 60 // IV_MIN)

    OUTPUT_DIR.mkdir(exist_ok=True)
    random.seed(42)

    total_dias = args.back + args.forward
    print("DAMP Life Stories Generator v2")
    print(f"  Labels     : sana | subclinica | clinica")
    print(f"  Desde      : {start:%Y-%m-%d %H:%M}  ({args.back} días atrás)")
    print(f"  Hasta      : {end:%Y-%m-%d %H:%M}  ({args.forward} días adelante)")
    print(f"  Total      : {total_dias} días  ({n_total} registros/vaca)")
    print(f"  Destino    : ./{OUTPUT_DIR}/\n")

    for cow_id, label, fn, personalidad in RODEO:
        rows = generar_vaca(cow_id, label, fn, personalidad, start, n_total)
        path = OUTPUT_DIR / f"cow_{cow_id:03d}_{label}_{personalidad}.csv"
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows)
        print(f"  ✓ COW_{cow_id:03d}  [{label:>10}]  [{personalidad:>12}]  → {path.name}")

    print(f"\n✓ {len(RODEO) * n_total:,} registros totales en ./{OUTPUT_DIR}/")
    print(f"\nCron sugerido (crontab -e):")
    print(f"  */5 * * * * cd /ruta/damp && python sender.py >> logs/sender.log 2>&1")
    print(f"\nCuando se agoten los {args.forward} días adelante, regenerá con:")
    print(f"  python life_stories.py --back 0 --forward 7")

if __name__ == "__main__":
    main()