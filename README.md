# damp
## Arquitectura
<img width="1440" height="2304" alt="image" src="https://github.com/user-attachments/assets/8d5c8980-33eb-46e3-8e01-98f25d30a956" />

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
