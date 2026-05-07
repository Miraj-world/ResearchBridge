from __future__ import annotations

import os
import shutil
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import db
from .repository import repo
from .schemas import (
    ApiError,
    ApiResponse,
    ChatRequest,
    CompareRequest,
    ProcessRequest,
    ProcessingState,
    ReprocessLevelRequest,
    UserLevel,
)
from .services.parser import ensure_upload_dir, parse_pdf_to_markdown
from .services.pipeline import compare_documents, grounded_chat_answer, process_markdown_to_document


def _request_id() -> str:
    return str(uuid.uuid4())


def ok(data: Any, request_id: str | None = None) -> dict[str, Any]:
    return ApiResponse(ok=True, data=data, error=None, request_id=request_id or _request_id()).model_dump()


def fail(code: str, message: str, details: dict[str, Any] | None = None, request_id: str | None = None) -> dict[str, Any]:
    err = ApiError(code=code, message=message, details=details or {})
    return ApiResponse(ok=False, data=None, error=err, request_id=request_id or _request_id()).model_dump()


def _set_state(paper_id: str, state: ProcessingState, last_error: dict[str, Any] | None = None) -> None:
    repo.update_job(
        paper_id,
        {
            "processing.state": state.value,
            "processing.last_error": last_error,
        },
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_upload_dir(settings.upload_dir)
    db.connect()
    yield
    db.close()


app = FastAPI(title="ResearchBridge MVP API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, Any]:
    return ok({"status": "healthy"})


@app.post("/api/v1/upload")
async def upload(file: UploadFile = File(...)) -> dict[str, Any]:
    rid = _request_id()
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        return fail("UPLOAD_INVALID_FILE", "Only PDF files are allowed", {"filename": file.filename}, rid)

    paper_id = str(uuid.uuid4())
    target_path = Path(settings.upload_dir) / f"{paper_id}.pdf"
    with target_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    repo.create_job(paper_id=paper_id, source_file=file.filename, file_path=str(target_path))
    repo.push_audit(paper_id, "uploaded", "upload_received", {"filename": file.filename})
    return ok({"paper_id": paper_id, "source_file": file.filename, "status": ProcessingState.uploaded.value}, rid)


@app.post("/api/v1/process")
def process(req: ProcessRequest) -> dict[str, Any]:
    rid = _request_id()
    job = repo.get_job(req.paper_id)
    if not job:
        return fail("NOT_FOUND", "paper_id not found", {"paper_id": req.paper_id}, rid)

    try:
        _set_state(req.paper_id, ProcessingState.parsing)
        repo.push_audit(req.paper_id, "parsing", "stage_started", {"state": "parsing"})
        parse_started = time.perf_counter()
        parse_result = parse_pdf_to_markdown(job["file_path"])
        parse_duration_ms = int((time.perf_counter() - parse_started) * 1000)
        _set_state(req.paper_id, ProcessingState.parsed)
        repo.update_job(
            req.paper_id,
            {
                "processing.timings_ms.parsing": parse_duration_ms,
                "processing.parser_path": parse_result.parser_path,
                "intermediate.markdown": parse_result.markdown,
            },
        )
        repo.push_audit(
            req.paper_id,
            "parsed",
            "stage_completed",
            {"parser_path": parse_result.parser_path, "timings_ms": parse_result.timings_ms},
        )

        _set_state(req.paper_id, ProcessingState.chunked)
        _set_state(req.paper_id, ProcessingState.tagged)
        _set_state(req.paper_id, ProcessingState.extracting)
        _set_state(req.paper_id, ProcessingState.verifying)
        _set_state(req.paper_id, ProcessingState.aggregated)
        _set_state(req.paper_id, ProcessingState.adapted)

        title = os.path.splitext(job["source_file"])[0]
        processed_doc, internal = process_markdown_to_document(
            paper_id=req.paper_id,
            title=title,
            source_file=job["source_file"],
            markdown=parse_result.markdown,
            user_level=req.user_level,
            parser_path=parse_result.parser_path,
            existing_audit=job.get("audit", []),
            timings_seed={"parsing": parse_duration_ms, **parse_result.timings_ms},
        )
        repo.upsert_processed_paper(req.paper_id, processed_doc)
        _set_state(req.paper_id, ProcessingState.completed)
        repo.update_job(
            req.paper_id,
            {
                "intermediate.internal": internal,
                "processing.timings_ms": processed_doc["processing"]["timings_ms"],
            },
        )
        repo.push_audit(req.paper_id, "completed", "processing_finished", {"user_level": req.user_level.value})
        return ok({"paper_id": req.paper_id, "state": ProcessingState.completed.value}, rid)

    except RuntimeError as e:
        code = "PARSER_FAILED" if str(e) == "PARSER_FAILED" else "INTERNAL_ERROR"
        err = {"stage": "parsing", "recoverable": False, "hint": "Try a clearer PDF or check parser dependencies."}
        _set_state(req.paper_id, ProcessingState.failed, {"code": code, "message": str(e), "details": err})
        repo.push_audit(req.paper_id, "failed", "stage_failed", {"code": code, "message": str(e)})
        return fail(code, str(e), err, rid)
    except Exception as e:
        err = {"stage": "processing", "recoverable": True, "hint": "Retry process for this paper."}
        _set_state(req.paper_id, ProcessingState.failed, {"code": "INTERNAL_ERROR", "message": str(e), "details": err})
        repo.push_audit(req.paper_id, "failed", "stage_failed", {"code": "INTERNAL_ERROR", "message": str(e)})
        return fail("INTERNAL_ERROR", str(e), err, rid)


@app.get("/api/v1/status/{paper_id}")
def status(paper_id: str) -> dict[str, Any]:
    rid = _request_id()
    job = repo.get_job(paper_id)
    if not job:
        return fail("NOT_FOUND", "paper_id not found", {"paper_id": paper_id}, rid)
    return ok(
        {
            "paper_id": paper_id,
            "state": job.get("processing", {}).get("state", ProcessingState.uploaded.value),
            "last_error": job.get("processing", {}).get("last_error"),
        },
        rid,
    )


@app.get("/api/v1/papers/{paper_id}")
def get_paper(paper_id: str) -> dict[str, Any]:
    rid = _request_id()
    paper = repo.get_processed_paper(paper_id)
    if not paper:
        return fail("NOT_FOUND", "processed paper not found", {"paper_id": paper_id}, rid)
    return ok(paper, rid)


@app.post("/api/v1/chat")
def chat(req: ChatRequest) -> dict[str, Any]:
    rid = _request_id()
    paper = repo.get_processed_paper(req.paper_id)
    if not paper:
        return fail("NOT_FOUND", "processed paper not found", {"paper_id": req.paper_id}, rid)
    level = req.user_level or UserLevel(paper.get("user_level", UserLevel.intermediate.value))
    answer = grounded_chat_answer(paper, req.question, level)
    return ok(answer, rid)


@app.post("/api/v1/compare")
def compare(req: CompareRequest) -> dict[str, Any]:
    rid = _request_id()
    left = repo.get_processed_paper(req.left_paper_id)
    right = repo.get_processed_paper(req.right_paper_id)
    if not left or not right:
        return fail(
            "NOT_FOUND",
            "one or both processed papers not found",
            {"left_paper_id": req.left_paper_id, "right_paper_id": req.right_paper_id},
            rid,
        )
    payload = compare_documents(left, right)
    return ok(payload, rid)


@app.post("/api/v1/reprocess-level")
def reprocess_level(req: ReprocessLevelRequest) -> dict[str, Any]:
    rid = _request_id()
    paper = repo.get_processed_paper(req.paper_id)
    job = repo.get_job(req.paper_id)
    if not paper or not job:
        return fail("NOT_FOUND", "paper_id not found", {"paper_id": req.paper_id}, rid)

    markdown = job.get("intermediate", {}).get("markdown")
    if not markdown:
        return fail(
            "BAD_REQUEST",
            "Cannot reprocess level because source markdown is missing.",
            {"paper_id": req.paper_id},
            rid,
        )

    parser_path = paper.get("processing", {}).get("parser_path", "unknown")
    rebuilt, internal = process_markdown_to_document(
        paper_id=req.paper_id,
        title=paper["title"],
        source_file=paper["source_file"],
        markdown=markdown,
        user_level=req.target_user_level,
        parser_path=parser_path,
        existing_audit=job.get("audit", []),
        timings_seed=paper.get("processing", {}).get("timings_ms", {}),
    )
    repo.upsert_processed_paper(req.paper_id, rebuilt)
    repo.update_job(req.paper_id, {"intermediate.internal": internal, "processing.state": ProcessingState.completed.value})
    repo.push_audit(req.paper_id, "adapted", "reprocess_level", {"target_user_level": req.target_user_level.value})
    return ok(rebuilt, rid)
