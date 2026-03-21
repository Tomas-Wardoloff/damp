"""
DAMP v3 — solapamiento realista, objetivo AUC 0.85-0.90
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

np.random.seed(42)

N_DIAS=3; INTERVALO_MIN=5
N_REGISTROS=(N_DIAS*24*60)//INTERVALO_MIN

RODEO={"sana":list(range(1,15)),"subclinica":list(range(15,18)),"clinica":list(range(18,21))}

PARAMS={
    "sana":      {"temp_media":38.6,"temp_std":0.55,"hr_media":65.0,"hr_std":8.0,"rmssd_media":40.0,"rmssd_std":10.0,"velocidad_media":1.7,"velocidad_std":0.8,"prob_rumia":0.52,"prob_vocal":0.08},
    "subclinica":{"temp_media":39.0,"temp_std":0.60,"hr_media":73.0,"hr_std":9.0,"rmssd_media":32.0,"rmssd_std":9.0,"velocidad_media":1.3,"velocidad_std":0.7,"prob_rumia":0.42,"prob_vocal":0.14},
    "clinica":   {"temp_media":40.2,"temp_std":0.65,"hr_media":88.0,"hr_std":11.0,"rmssd_media":16.0,"rmssd_std":5.5,"velocidad_media":0.5,"velocidad_std":0.3,"prob_rumia":0.13,"prob_vocal":0.26},
}

ATIPICOS={3:"estres_termico",7:"muy_activa",11:"sedentaria",16:"remision",19:"fluctuante"}

def modificar_atipico(aid, p):
    p=p.copy(); t=ATIPICOS[aid]
    if t=="estres_termico": p["temp_media"]+=0.5; p["hr_media"]+=6; p["rmssd_media"]-=6
    elif t=="muy_activa": p["velocidad_media"]+=0.8; p["prob_vocal"]+=0.05
    elif t=="sedentaria": p["velocidad_media"]-=0.6; p["prob_rumia"]-=0.10; p["hr_media"]+=5
    elif t=="remision": p["temp_media"]-=0.3; p["hr_media"]-=8; p["rmssd_media"]+=8
    elif t=="fluctuante": p["temp_std"]+=0.4; p["hr_std"]+=6; p["rmssd_std"]+=4
    return p

def circ(h): return 0.55+0.45*(np.exp(-0.5*((h-7)/1.5)**2)+np.exp(-0.5*((h-17)/1.5)**2))

def evento(i, aid):
    s=np.random.get_state(); np.random.seed(aid*1000+i)
    r=np.random.random()<0.03; np.random.set_state(s); return r

def generar_animal(aid, estado):
    p=PARAMS[estado].copy()
    if aid in ATIPICOS: p=modificar_atipico(aid,p)
    t0=datetime(2025,6,1,6,0,0)
    lat0=-34.6037+np.random.uniform(-0.08,0.08)
    lon0=-60.9265+np.random.uniform(-0.08,0.08)
    lat,lon=lat0,lon0
    radio={"sana":0.010,"subclinica":0.005,"clinica":0.002}[estado]
    rows=[]
    for i in range(N_REGISTROS):
        ts=t0+timedelta(minutes=i*INTERVALO_MIN)
        h=ts.hour+ts.minute/60.0; c=circ(h)
        rc=np.random.normal(0,1)  # ruido correlacionado
        prog=i/N_REGISTROS; drift=0.3*prog if estado!="sana" else 0
        ev=evento(i,aid)

        temp=np.random.normal(p["temp_media"]+drift,p["temp_std"])
        temp+=0.1*np.sin(2*np.pi*(h-6)/24)+rc*0.12+(np.random.uniform(0.3,0.8) if ev else 0)
        temp=round(float(np.clip(temp,36.5,42.5)),2)

        hr=np.random.normal(p["hr_media"],p["hr_std"])+rc*2.5+(np.random.uniform(3,10) if ev else 0)
        hr=round(float(np.clip(hr,38,130)),1)

        rmssd=round(float(max(4.0,np.random.normal(p["rmssd_media"],p["rmssd_std"])-rc*1.5)),1)
        sdnn=round(float(max(rmssd*1.05,rmssd*np.random.uniform(1.1,1.5))),1)

        pr=p["prob_rumia"]*(0.7+0.6*c)*(0.3 if ev else 1)
        hubo_rumia=int(np.random.random()<min(pr,1.0))
        hubo_vocal=int(np.random.random()<(p["prob_vocal"]+(0.15 if ev else 0)))

        vel=max(0.0,np.random.normal(p["velocidad_media"]*c,p["velocidad_std"])*(0.4 if ev else 1))
        vel=round(float(vel),2); metros=round(vel*(INTERVALO_MIN/60)*1000,1)
        paso=(vel/3600)*INTERVALO_MIN*60/111320
        lat=float(np.clip(lat+np.random.normal(0,paso*0.5),lat0-radio,lat0+radio))
        lon=float(np.clip(lon+np.random.normal(0,paso*0.5),lon0-radio,lon0+radio))

        rows.append({"label":estado,"timestamp":ts.strftime("%Y-%m-%d %H:%M:%S"),"animal_id":f"BOV_{aid:03d}",
            "temperatura_corporal_prom":temp,"hubo_rumia":hubo_rumia,"frec_cardiaca_prom":hr,
            "rmssd":rmssd,"sdnn":sdnn,"hubo_vocalizacion":hubo_vocal,
            "latitud":round(lat,6),"longitud":round(lon,6),
            "metros_recorridos":metros,"velocidad_movimiento_prom":vel})
    return rows

print("DAMP v3 — dataset con solapamiento realista\n")
todos=[]
for estado,ids in RODEO.items():
    for aid in ids:
        filas=generar_animal(aid,estado); todos.extend(filas)
        tag=f" ⚠ {ATIPICOS[aid]}" if aid in ATIPICOS else ""
        print(f"  ✓ BOV_{aid:03d}  [{estado:>10}]  {len(filas)} registros{tag}")

df=pd.DataFrame(todos)
print(f"\nShape: {df.shape[0]:,} × {df.shape[1]}")
print("\n── Promedios por estado ─────────────────────────")
cols=["temperatura_corporal_prom","frec_cardiaca_prom","rmssd","metros_recorridos"]
print(df.groupby("label")[cols].mean().round(2).to_string())
print("\n── Overlap sana vs subclinica ───────────────────")
for col in ["temperatura_corporal_prom","rmssd","frec_cardiaca_prom"]:
    s=df[df.label=="sana"][col]; u=df[df.label=="subclinica"][col]
    print(f"{col}: sana {s.mean():.1f}±{s.std():.1f}  sub {u.mean():.1f}±{u.std():.1f}")

out=Path(__file__).resolve().parent
df.to_csv(out/"damp_data.csv",index=False)
df.sample(100,random_state=42).sort_values("timestamp").to_csv(out/"damp_sample.csv",index=False)
print(f"\n✓ guardado en {out}")