# Backend - Livestock Health Monitoring (Mastitis MVP)

FastAPI backend for receiving collar readings, storing health data, and requesting mastitis status from an external AI service.

## Stack

- FastAPI
- PostgreSQL
- SQLAlchemy ORM
- Alembic
- Pydantic
- httpx

## Project Structure

```text
backend/
├── app/
│   ├── main.py
│   ├── core/
│   ├── modules/
│   │   ├── cow/
│   │   ├── collar/
│   │   ├── reading/
│   │   └── health/
│   ├── integrations/
│   └── shared/
├── alembic/
├── alembic.ini
└── requirements.txt
```

## Quick Start

1. Create env file:

```powershell
Copy-Item .env.example .env
```

2. Start dev server with one command:

```powershell
python .\run-dev.py
```

Server:

- http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs

## Migrations (Alembic)

Create migration:

```powershell
.\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "init_schema"
```

Apply migrations:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

## Endpoints

### Cows

- POST /cows
- GET /cows
- GET /cows/{id}

### Collars

- POST /collars
- POST /collars/{id}/assign/{cow_id}
- POST /collars/{id}/unassign

### Readings

- POST /readings
- GET /cows/{id}/readings?page=1&size=20

### Health / AI

- POST /health/analyze/{cow_id}?limit=5
- GET /health/status/{cow_id}?limit=5
- GET /health/history/{cow_id}

`POST /health/analyze/{cow_id}` takes the latest `limit` readings (default 5), sends them to:

`POST https://damp-machine-learning.onrender.com/predict`

and stores the returned status in `health_analyses`.

## Example Requests

Create cow:

```bash
curl -X POST http://127.0.0.1:8000/cows \
  -H "Content-Type: application/json" \
  -d '{
    "breed": "Holstein",
    "registration_date": "2026-03-20T19:00:00Z",
    "age_months": 42
  }'
```

Create collar:

```bash
curl -X POST http://127.0.0.1:8000/collars
```

Assign collar to cow:

```bash
curl -X POST http://127.0.0.1:8000/collars/1/assign/1
```

Create reading:

```bash
curl -X POST http://127.0.0.1:8000/readings \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2026-03-20T19:10:00Z",
    "collar_id": 1,
    "temperatura_corporal_prom": 38.7,
    "hubo_rumia": true,
    "frec_cardiaca_prom": 68.2,
    "rmssd": 27.5,
    "sdnn": 40.1,
    "hubo_vocalizacion": false,
    "latitud": -34.6001,
    "longitud": -58.3845,
    "metros_recorridos": 112.4,
    "velocidad_movimiento_prom": 1.9
  }'
```

Analyze health:

```bash
curl -X POST http://127.0.0.1:8000/health/analyze/1
```

Get current status:

```bash
curl http://127.0.0.1:8000/health/status/1
```

Get status history:

```bash
curl http://127.0.0.1:8000/health/history/1
```
