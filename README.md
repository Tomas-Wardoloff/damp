# DAMP

[![Access the Application](https://img.shields.io/badge/Access_the_Application-Vercel-black?style=for-the-badge&logo=vercel)](https://damp-front.vercel.app/)

## Demo
Watch the project demo on YouTube:
[https://youtu.be/TafMqvO5Wco](https://youtu.be/TafMqvO5Wco)

## Introduction
**DAMP (Distributed Animal Monitoring Platform)** is an advanced biometric monitoring platform designed for the livestock sector. It uses high-frequency sensors (smart collars) and Machine Learning models to detect diseases and physiological changes.

---

## Project Architecture

The project is designed as a comprehensive animal health monitoring platform, consisting of three main services that interact with each other:

### 1. Frontend (Next.js)
Located in [frontend/](frontend/), it is the modern user interface built with **Next.js 16**, **React 19**, and **Tailwind CSS**.
- **Data Visualization:** Dynamic charts with **Recharts** for biometric metrics.
- **Geolocation:** Interactive maps with **Leaflet** for real-time livestock tracking.
- **Dashboard:** Central panel with summary metrics and health alerts.

### 2. Backend (FastAPI)
Located in [backend/](backend/), it acts as the core of business logic and data management.
- **Framework:** **FastAPI** for a high-performance REST API.
- **Persistence:** **PostgreSQL** managed through **SQLAlchemy ORM** and database migrations with **Alembic**.
- **Modules:** Modular architecture that separates responsibilities into `cow` (livestock), `collar` (sensors), `reading` (biometric readings), and `health` (health).
- **AI Integration:** Connects with the ML service to obtain automatic health diagnoses.

### 3. Machine Learning (FastAPI + SciKit-Learn)
Located in [machine-learning/](machine-learning/), it is the service specialized in predictive analysis.
- **Prediction:** Service that exposes a trained model for detecting mastitis and other health conditions based on collar readings.
- **Data Generation:** Includes scripts for life story simulation and synthetic test dataset generation.

## Data Strategy and Initial Operation

To ensure the system is functional from the start, the project implements a robust synthetic data generation strategy based on real research:

1.  **Problem Context and Sensors:** The project infrastructure is designed under the premise that **each animal has a collar with multi-biometric sensors** that send data continuously every **5 minutes**. Given the lack of a public dataset that strictly met this requirement for high frequency and sensor diversity, a sophisticated simulation technique was chosen.
2.  **Research Premises:** The scientific basis and the collection of original data are detailed in the document [Research.md](Research.md).
3.  **Synthetic Generation:** Based on research premises (such as physiological constants for temperature, heart rate, and movement patterns by health status), a **Vectorized Generator** was developed in [backend/app/modules/seed/service.py](backend/app/modules/seed/service.py). This generator uses **NumPy** to simulate thousands of biometric readings with:
    - Circadian cycles and thermal variations.
    - Correlated noise between sensors (simulating real failures).
    - Specific health patterns (healthy, mastitis, heat, febrile, digestive).
3.  **Pre-loading Historical Data:** The system includes a Seed service that pre-loads the database with:
    - **Biometric Readings:** 7-day history for each animal, essential for ML models to identify trends.
    - **Health Analysis:** History of previous diagnoses to populate evolution charts.

This pre-loading ensures that upon starting the product, the user already has full dashboards, maps with trajectories, and AI models capable of making inferences on pre-existing data.

## Data Flow
1. **Collars** send biometric readings to the **Backend**.
2. The **Backend** persists data in **PostgreSQL**.
3. The **Backend** requests a prediction from the **Machine Learning** service.
4. The **Frontend** consumes the Backend API to display health status, alerts, and maps to the end user.

## API (FastAPI)

### Run dev (JavaScript style)

Use a single command and the script does everything:

```powershell
.\run-dev.ps1
```

If you prefer to run everything with Python:

```powershell
python .\run-dev.py
```

If you are on CMD instead of PowerShell:

```cmd
run-dev.cmd
```

The script:

- Creates `.venv` if it doesn't exist
- Installs dependencies from `requirements.txt`
- Starts the server with reload

### 1. Create and activate virtual environment

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Environment variables

```powershell
Copy-Item .env.example .env
```

### 4. Start server with Uvicorn

```powershell
uvicorn app.main:app --reload
```

The API will be available at:

- http://127.0.0.1:8000/
- http://127.0.0.1:8000/docs
