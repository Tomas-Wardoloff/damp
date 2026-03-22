# Research & Data Acquisition

# Referencias científicas — DAMP
> Parámetros fisiológicos bovinos usados en el generador de datos sintéticos

---

## Generación de Datos Sintéticos

Para asegurar un **funcionamiento inicial** robusto y permitir el entrenamiento de modelos de Machine Learning sin depender de una infraestructura de sensores física desplegada durante meses, hemos desarrollado un motor de simulación avanzada en el [SeedService](backend/app/modules/seed/service.py).

### Metodología de Simulación

La generación de datos no es aleatoria, sino que sigue una arquitectura de simulación basada en tres pilares:

#### 1. Modelado Fisiológico (Vectores de Estado)
Utilizamos una matriz de parámetros base (temperatura, frecuencia cardíaca, HRV, frecuencia ruminal) extraída de las referencias científicas anteriores. Cada estado de salud (`Sana`, `Mastitis`, `Celo`, `Febril`, `Digestivo`) actúa como un perfil que define:
- **Media ($μ$):** Valor esperado para la métrica en ese estado.
- **Desviación Estándar ($σ$):** Variabilidad natural del individuo.

#### 2. Dinámicas Temporales y Ciclos Circadianos
Para que los datos sean realistas temporalmente, el generador aplica:
- **Variación Circadiana:** Modelamos la temperatura y actividad con picos en horas de pastoreo (7:00 y 17:00) y descensos nocturnos mediante funciones gaussianas.
- **Transiciones de Estado:** Las "historias de vida" de las vacas simulan el progreso de una enfermedad (ej. una vaca que comienza sana, entra en cuadro febril y luego se recupera), permitiendo al modelo aprender la *tendencia* y no solo el valor puntual.

#### 3. Simulación de Errores y Ruido Real
Para entrenar modelos resilientes, introducimos artificialmente:
- **Ruido Correlacionado:** Simulación de interferencias ambientales que afectan a múltiples sensores simultáneamente.
- **Fallas de Sensor (Outliers):** Probabilidad del ~0.8% de lecturas erráticas o nulas (dropouts) para forzar al modelo a manejar datos incompletos.
- **Artefactos Cardíacos:** Picos de frecuencia cardíaca aleatorios que no corresponden a patologías, simulando movimientos bruscos o estrés momentáneo.

### Implementación Técnica
El proceso se realiza de forma **vectorizada** utilizando **NumPy**, logrando generar historiales completos (ej. 21 vacas durante 7 días con lecturas cada 5 minutos) en menos de 5 segundos. Esta velocidad es crítica para entornos de desarrollo y pruebas de integración continua.

---

## Temperatura corporal
> `BASE = 38.6°C` · mastitis `+1.8°C` · febril `+1.7°C`

- Kim et al. (2019) — *Real-time temperature monitoring for early detection of mastitis*
  https://www.sciencedirect.com/science/article/abs/pii/S0168169918308494

- PMC4698711 — *Body Temperature Monitoring Using Subcutaneously Implanted Thermo-loggers in Cattle*
  https://pmc.ncbi.nlm.nih.gov/articles/PMC4698711/

---

## Frecuencia cardíaca
> `BASE = 65 bpm` · mastitis `+24` · celo `+9` · rango normal 60–80 bpm en reposo

- PMC4546236 — *Heart Rate and HRV in Dairy Cows with Different Temperament*
  https://pmc.ncbi.nlm.nih.gov/articles/PMC4546236/

---

## HRV — RMSSD y SDNN
> `BASE rmssd = 40 ms` · mastitis `−26 ms` · digestivo `−14 ms` · SDNN = rmssd × 1.1–1.45

- MDPI Sensors (2018) — *Recording HRV of Dairy Cows to the Cloud*
  https://www.mdpi.com/1424-8220/18/8/2541

- OUCI — *Maternal, fetal and neonatal HR and HRV in Holstein cattle*
  https://ouci.dntb.gov.ua/en/works/lxeEPq09/

- Bovine Vet (2021) — *Heart Rate Variability Can Help Assess Stress and Pain*
  https://www.bovinevetonline.com/news/veterinary-education/heart-rate-variability-can-help-assess-stress-and-pain

---

## Movimiento / velocidad — celo
> celo `+2.8 m/s` · patrón nocturno gaussiano centrado en 23hs · mastitis `−1.1 m/s`

- Cambridge Animal (2017) — *Behavioral signs of estrus and fully automated detection systems*
  https://www.cambridge.org/core/journals/animal/article/review-behavioral-signs-of-estrus-and-the-potential-of-fully-automated-systems-for-detection-of-estrus-in-dairy-cattle/0C4FCAEE6973AB21FC33C02C8403AC51

- Frontiers in Animal Science (2023) — *Behavioral changes to detect estrus using ear-sensor accelerometer*
  https://www.frontiersin.org/journals/animal-science/articles/10.3389/fanim.2023.1149085/full

- ScienceDirect (2019) — *Calving and estrus detection using localization + accelerometer*
  https://www.sciencedirect.com/science/article/abs/pii/S0168169919315261

- PMC7401617 — *ML Techniques for Estrus Detection Using Location and Acceleration Data*
  https://pmc.ncbi.nlm.nih.gov/articles/PMC7401617/

---

## Rumia
> `BASE p_rumia = 0.52` · boost nocturno `+60%` · digestivo `−0.44` · mastitis `−0.42`
> Vacas sanas rumiaron 7–8 horas/día, principalmente de noche

- PMC8547861 — *Using rumination time to manage health and reproduction in dairy cattle*
  https://pmc.ncbi.nlm.nih.gov/articles/PMC8547861/

- PMC9994596 — *Variations in 24h temporal patterns of grazing and rumination*
  https://pmc.ncbi.nlm.nih.gov/articles/PMC9994596/

- Allflex White Paper — *Rumination Monitoring in Dairy Cattle*
  https://www.allflex.global/wp-content/uploads/2021/09/Rumination-Monitoring-White-Paper.pdf

---

## Ritmo circadiano
> Función `circ(h)` con picos a las 7am y 17pm · temperatura `−0.25°C` de noche · HR `−7 bpm` de noche · velocidad `~15%` de la diurna

- Frontiers in Animal Science (2022) — *Ultra- and Circadian Activity Rhythms of Dairy Cows in AMS*
  https://www.frontiersin.org/journals/animal-science/articles/10.3389/fanim.2022.839906/full

---

## Sensores wearable — validación general del enfoque

- PMC8044875 — *Systematic Review: Validated Sensor Technologies for Welfare Assessment of Dairy Cattle*
  https://pmc.ncbi.nlm.nih.gov/articles/PMC8044875/

- PMC8532812 — *Wearable Wireless Biosensor Technology for Monitoring Cattle*
  https://pmc.ncbi.nlm.nih.gov/articles/PMC8532812/

