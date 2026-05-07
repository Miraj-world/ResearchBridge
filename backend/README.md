# AI Research Paper Learning & Implementation Explainer (Backend)

Backend service for uploading AI/ML PDFs, running extraction and verification pipeline stages, and serving explanation/chat/compare APIs.

## API Endpoints

- `POST /upload`
- `GET /paper/{paper_id}`
- `POST /chat`
- `GET /papers`
- `POST /compare`
- `GET /health`

All API responses use this envelope:

```json
{
  "success": true,
  "data": {},
  "error": null
}
```

## Tech Stack

- FastAPI
- Anthropic API (`claude-sonnet-4-20250514` extractor, `claude-haiku-4-5-20251001` verifier)
- Docling (primary PDF to Markdown)
- pytesseract @ 300 DPI (OCR fallback)
- MongoDB local (`processed_papers`) with JSON fallback storage

## Prerequisites

1. Python `3.12` or `3.13` on Windows
2. Node.js (frontend)
3. MongoDB local (optional but recommended)
4. Tesseract OCR installed and available on PATH

## Environment Variables

Copy `backend/.env.example` to `.env` and set:

- `ANTHROPIC_API_KEY=your_key_here`
- `MONGODB_URI=mongodb://localhost:27017`
- `DB_NAME=research_explainer`

## Install

From repo root:

```powershell
pip install -r backend/requirements.txt
cd frontend
npm install
```

## Run (Recommended)

From repo root:

```powershell
.\start.bat
```

### What start.bat does

- Starts backend and frontend in separate windows
- Uses `backend/.venv/Scripts/python.exe` for backend (Python 3.12 recommended)
- Runs backend dependency preflight (`backend/tools/preflight_check.py`) before launching Uvicorn
- Blocks backend startup if PDF extraction dependencies are missing

## Logs

Error logs are written to:

- `logs/backend.error.log`
- `logs/frontend.error.log`

## PDF Ingestion Behavior

- Stage 1: Docling extraction
- Stage 2: OCR fallback (PyMuPDF + pytesseract at 300 DPI)
- On complete failure: API returns
  - `Could not extract text from this PDF. It may be corrupted or image-only.`

The backend now records parser-specific diagnostics (`docling_error`, `ocr_error`) to error logs so dependency issues are visible.

## Troubleshooting

### UI shows `Failed to fetch`

This means frontend cannot reach backend at `http://localhost:8000`.

Check in order:

1. Backend window output from `start.bat`
2. `logs/backend.error.log`
3. Preflight output for missing dependencies

### Common dependency fixes

```powershell
pip install -r backend/requirements.txt
pip install docling pymupdf pytesseract
winget install UB-Mannheim.TesseractOCR
tesseract --version
```

## Manual Run (Optional)

Backend:

```powershell
python -m uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```powershell
cd frontend
npm run dev
```

