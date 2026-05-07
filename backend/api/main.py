from __future__ import annotations

import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.models.schemas import (
    AggregationInput,
    ApiEnvelope,
    ChatRequest,
    ChatResponse,
    CompareRequest,
    CompareResponse,
    JobRecord,
    PaperListItem,
    ProcessingStage,
    UploadResponse,
    UserLevel,
    utc_now_iso,
)
from backend.pipeline.adapter import adapt_level
from backend.pipeline.aggregator import aggregate_results
from backend.pipeline.chunking import chunk_markdown
from backend.pipeline.extractor import extract_claims
from backend.pipeline.ingestion import IngestionError, ingest_pdf
from backend.pipeline.llm_client import AnthropicJSONClient, LLMClientError
from backend.pipeline.role_assignment import assign_roles
from backend.pipeline.verifier import verify_claims
from backend.storage.db import StorageService


BASE_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BASE_DIR.parent
LOG_DIR = REPO_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

UPLOAD_DIR = BASE_DIR / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "research_explainer")

EXTRACTOR_MODEL = "claude-sonnet-4-20250514"
VERIFIER_MODEL = "claude-haiku-4-5-20251001"

error_logger = logging.getLogger("researchbridge.error")
_log_handler: logging.Handler | None = None
if not error_logger.handlers:
    # Use stderr handler to avoid Windows file-lock issues with Uvicorn reload workers.
    # start.bat already redirects stderr to logs/backend.error.log.
    _log_handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")
    _log_handler.setFormatter(formatter)
    error_logger.addHandler(_log_handler)
    error_logger.setLevel(logging.INFO)
    error_logger.propagate = False

ingestion_logger = logging.getLogger("researchbridge.ingestion")
if not ingestion_logger.handlers and _log_handler is not None:
    ingestion_logger.addHandler(_log_handler)
    ingestion_logger.setLevel(logging.INFO)
    ingestion_logger.propagate = False

storage = StorageService(
    mongodb_uri=MONGODB_URI,
    db_name=DB_NAME,
    json_dir=str(BASE_DIR / "data" / "json_fallback"),
)
storage.connect()

llm_client: AnthropicJSONClient | None = None
if ANTHROPIC_API_KEY:
    try:
        llm_client = AnthropicJSONClient(api_key=ANTHROPIC_API_KEY, timeout_seconds=30, max_attempts=2)
    except LLMClientError:
        llm_client = None


app = FastAPI(title="AI Research Paper Learning & Implementation Explainer", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def ok(data: Any) -> dict[str, Any]:
    return ApiEnvelope[Any](success=True, data=data, error=None).model_dump(mode="json")


def fail(message: str) -> dict[str, Any]:
    return ApiEnvelope[Any](success=False, data=None, error=message).model_dump(mode="json")


def error_response(message: str, status_code: int) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=fail(message))


def _set_stage(job: JobRecord, stage: ProcessingStage) -> JobRecord:
    if not job.stage_history or job.stage_history[-1] != stage:
        job.stage_history.append(stage)
    job.status = stage
    storage.save_job(job)
    return job


def _ensure_llm() -> AnthropicJSONClient:
    if llm_client is None:
        raise RuntimeError("ANTHROPIC_API_KEY is missing")
    return llm_client


def _text_score(query: str, text: str) -> int:
    q_terms = [term for term in query.lower().split() if len(term) > 2]
    source = text.lower()
    return sum(1 for term in q_terms if term in source)


@app.get("/health")
def health() -> dict[str, Any]:
    return ok({"status": "healthy"})


@app.post("/upload")
async def upload(file: UploadFile = File(...), user_level: UserLevel = Form(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        return error_response("Only PDF files are supported", 400)

    paper_id = uuid4()
    title = Path(file.filename).stem
    pdf_path = UPLOAD_DIR / f"{paper_id}.pdf"

    with pdf_path.open("wb") as target:
        shutil.copyfileobj(file.file, target)

    job = JobRecord(
        paper_id=paper_id,
        source_file=file.filename,
        title=title,
        user_level=user_level,
        status=ProcessingStage.parsing,
        stage_history=[ProcessingStage.parsing],
        created_at=utc_now_iso(),
    )
    storage.save_job(job)

    try:
        ingestion = ingest_pdf(str(pdf_path))
    except IngestionError as exc:
        error_logger.error(
            "PDF ingestion failed for paper_id=%s source_file=%s docling_error=%s ocr_error=%s",
            paper_id,
            file.filename,
            exc.docling_error or "none",
            exc.ocr_error or "none",
        )
        return error_response(exc.actionable_error_message(), 400)
    except RuntimeError as exc:
        error_logger.exception("Unexpected runtime error during upload for paper_id=%s", paper_id)
        return error_response(str(exc), 500)

    job.markdown = ingestion.markdown
    storage.save_job(job)

    _set_stage(job, ProcessingStage.chunking)
    section_chunks = chunk_markdown(ingestion.markdown)

    _set_stage(job, ProcessingStage.extracting)
    try:
        client = _ensure_llm()
    except RuntimeError as exc:
        return error_response(str(exc), 500)
    chunks_with_roles = assign_roles(section_chunks, client, VERIFIER_MODEL)
    extracted_claims, _skipped_chunk_ids = extract_claims(chunks_with_roles, client, EXTRACTOR_MODEL)

    _set_stage(job, ProcessingStage.verifying)
    chunk_map = {chunk.chunk_id: chunk.text for chunk in chunks_with_roles}
    verified_claims = verify_claims(extracted_claims, chunk_map, client, VERIFIER_MODEL)

    _set_stage(job, ProcessingStage.aggregation)
    aggregated = aggregate_results(
        AggregationInput(
            paper_id=paper_id,
            title=title,
            source_file=file.filename,
            user_level=user_level,
            chunks=chunks_with_roles,
            verified_claims=verified_claims,
        )
    )

    _set_stage(job, ProcessingStage.adaptation)
    adapted = adapt_level(aggregated)
    adapted.stage_history = list(job.stage_history) + [ProcessingStage.done]

    storage.save_processed_paper(adapted)
    _set_stage(job, ProcessingStage.done)

    response = UploadResponse(
        paper_id=paper_id,
        title=title,
        processed_at=adapted.processed_at,
        stage_history=adapted.stage_history,
    )
    return ok(response.model_dump(mode="json"))


@app.get("/paper/{paper_id}")
def get_paper(paper_id: UUID) -> dict[str, Any]:
    paper = storage.get_processed_paper(paper_id)
    if paper is None:
        return fail("Paper not found")
    return ok(paper.model_dump(mode="json"))


@app.get("/papers")
def list_papers() -> dict[str, Any]:
    papers: list[PaperListItem] = storage.list_papers()
    return ok([item.model_dump(mode="json") for item in papers])


@app.post("/chat")
def chat(request: ChatRequest):
    paper = storage.get_processed_paper(request.paper_id)
    if paper is None:
        return fail("Paper not found")

    ranked_chunks = sorted(
        paper.chunks,
        key=lambda chunk: _text_score(request.message, chunk.text),
        reverse=True,
    )
    top_chunks = [chunk for chunk in ranked_chunks if _text_score(request.message, chunk.text) > 0][:4]

    if not top_chunks:
        response = ChatResponse(
            response="This isn't covered in the uploaded paper.",
            referenced_sections=[],
            confidence=paper.problem.confidence,
        )
        return ok(response.model_dump(mode="json"))

    context = "\n\n".join([f"[{chunk.header}]\n{chunk.text}" for chunk in top_chunks])
    section_names = [chunk.header for chunk in top_chunks]

    chat_system = (
        "You are a research paper assistant. Answer ONLY from provided paper chunks. "
        "If not present, respond exactly: This isn't covered in the uploaded paper. "
        "Always mention section names used."
    )
    chat_user = f"Question: {request.message}\n\nPaper chunks:\n{context}"

    try:
        client = _ensure_llm()
        answer = client.call_text(
            model=EXTRACTOR_MODEL,
            system_prompt=chat_system,
            user_prompt=chat_user,
            max_tokens=500,
            temperature=0.0,
        )
    except RuntimeError as exc:
        return error_response(str(exc), 500)
    except LLMClientError:
        answer = "This isn't covered in the uploaded paper."

    chat_response = ChatResponse(
        response=answer,
        referenced_sections=section_names,
        confidence=paper.core_idea.confidence,
    )
    return ok(chat_response.model_dump(mode="json"))


@app.post("/compare")
def compare(request: CompareRequest) -> dict[str, Any]:
    paper_1 = storage.get_processed_paper(request.paper_id_1)
    paper_2 = storage.get_processed_paper(request.paper_id_2)

    if paper_1 is None or paper_2 is None:
        return fail("One or both papers were not found")

    payload = CompareResponse(paper_1=paper_1, paper_2=paper_2)
    return ok(payload.model_dump(mode="json"))
