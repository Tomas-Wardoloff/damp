import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

if sys.platform == "win32":
    VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
else:
    VENV_PYTHON = ROOT / ".venv" / "bin" / "python"

def run(command: list[str]) -> None:
    subprocess.run(command, check=True)

if not VENV_PYTHON.exists():
    print("[setup] Creating virtual environment (.venv)...")
    run([sys.executable, "-m", "venv", ".venv"])

print("[setup] Installing dependencies...")
run([str(VENV_PYTHON), "-m", "pip", "install", "-r", "requirements.txt"])

print("[dev] Starting FastAPI with uvicorn...")
run([str(VENV_PYTHON), "-m", "uvicorn", "app.main:app", "--reload"])