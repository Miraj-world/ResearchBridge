# AI Research Paper Learning & Implementation Explainer

Full-stack app to upload AI/ML research PDFs and generate implementation-focused, level-adapted explanations.

## Quick Start

1. Install backend dependencies:
   - `pip install -r backend/requirements.txt`
2. Install frontend dependencies:
   - `cd frontend && npm install`
3. Configure env vars in `.env` using `backend/.env.example`
4. Create backend venv on Python 3.12 and install deps:
   - `py -3.12 -m venv backend/.venv`
   - `backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt`
5. Start both services:
   - `./start.bat`

## Services

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`

## Startup Preflight

`start.bat` runs a backend dependency preflight before Uvicorn starts.

If preflight fails, backend will not start and you will see missing dependencies in the backend window.

## Logs

`start.bat` writes error logs to `./logs`:

- `backend.error.log`
- `frontend.error.log`

## Common Error

If the UI shows `Failed to fetch`, backend is not reachable (usually because backend preflight failed or backend is not running). Check:

- backend terminal window
- `logs/backend.error.log`

For backend details and API docs, see `backend/README.md`.

