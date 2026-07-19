# Backend

FastAPI backend for the Job Aggregator.

## Start the server

Run these commands from the `backend` folder in PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy ..\.env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

If you see `winerror 10048`, port `8000` is already in use. Stop the other
backend process, or start this one on a different port:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

## Endpoints

- `http://127.0.0.1:8000/health` - health check
- `http://127.0.0.1:8000/docs` - Swagger UI
