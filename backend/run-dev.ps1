$ErrorActionPreference = "Stop"

$pythonInVenv = ".\.venv\Scripts\python.exe"

if (-not (Test-Path $pythonInVenv)) {
    Write-Host "[setup] Creating virtual environment (.venv)..."
    python -m venv .venv
}

Write-Host "[setup] Installing dependencies..."
& $pythonInVenv -m pip install -r requirements.txt

Write-Host "[dev] Starting FastAPI with uvicorn..."
& $pythonInVenv -m uvicorn app.main:app --reload
