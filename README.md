# damp
## Arquitectura del Proyecto

El proyecto está diseñado como una plataforma integral de monitoreo de salud animal, compuesta por tres servicios principales que interactúan entre sí:

### 1. Frontend (Next.js)
Ubicado en [frontend/](frontend/), es la interfaz de usuario moderna construida con **Next.js 16**, **React 19** y **Tailwind CSS**.
- **Visualización de Datos:** Gráficos dinámicos con **Recharts** para métricas biométricas.
- **Geolocalización:** Mapas interactivos con **Leaflet** para el seguimiento en tiempo real del ganado.
- **Dashboard:** Panel central con métricas resumen y alertas de salud.

### 2. Backend (FastAPI)
Ubicado en [backend/](backend/), actúa como el núcleo de lógica de negocios y gestión de datos.
- **Framework:** **FastAPI** para una API REST de alto rendimiento.
- **Persistencia:** **PostgreSQL** gestionado a través de **SQLAlchemy ORM** y migraciones de base de datos con **Alembic**.
- **Módulos:** Arquitectura modular que separa responsabilidades en `cow` (ganado), `collar` (sensores), `reading` (lecturas biométricas) y `health` (salud).
- **Integración AI:** Conecta con el servicio de ML para obtener diagnósticos de salud automáticos.

### 3. Machine Learning (FastAPI + SciKit-Learn)
Ubicado en [machine-learning/](machine-learning/), es el servicio especializado en análisis predictivo.
- **Predicción:** Servicio que expone un modelo entrenado para la detección de mastitis y otras condiciones de salud basándose en las lecturas de los collares.
- **Generación de Datos:** Incluye scripts para la simulación de historias de vida y generación de datasets sintéticos de prueba.

## Flujo de Datos
1. Los **Collares** envían lecturas biométricas al **Backend**.
2. El **Backend** persiste los datos en **PostgreSQL**.
3. El **Backend** solicita una predicción al servicio de **Machine Learning**.
4. El **Frontend** consume la API del Backend para mostrar el estado de salud, alertas y mapas al usuario final.

## API (FastAPI)

### Run dev (estilo JavaScript)

Usa un solo comando y el script hace todo:

```powershell
.\run-dev.ps1
```

Si prefieres correr todo con Python:

```powershell
python .\run-dev.py
```

Si estas en CMD en lugar de PowerShell:

```cmd
run-dev.cmd
```

El script:

- Crea `.venv` si no existe
- Instala dependencias de `requirements.txt`
- Levanta el servidor con reload

### 1. Crear y activar entorno virtual

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Instalar dependencias

```powershell
pip install -r requirements.txt
```

### 3. Variables de entorno

```powershell
Copy-Item .env.example .env
```

### 4. Levantar servidor con Uvicorn

```powershell
uvicorn app.main:app --reload
```

La API quedara disponible en:

- http://127.0.0.1:8000/
- http://127.0.0.1:8000/docs
