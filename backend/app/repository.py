from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pymongo import ReturnDocument

from .db import db
from .schemas import ProcessingState


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


class PaperRepository:
    def create_job(self, paper_id: str, source_file: str, file_path: str) -> dict[str, Any]:
        doc = {
            "paper_id": paper_id,
            "source_file": source_file,
            "file_path": file_path,
            "created_at": _ts(),
            "updated_at": _ts(),
            "processing": {
                "state": ProcessingState.uploaded.value,
                "timings_ms": {},
                "parser_path": None,
                "last_error": None,
            },
            "audit": [],
            "intermediate": {},
        }
        db.jobs.insert_one(doc)
        return doc

    def get_job(self, paper_id: str) -> dict[str, Any] | None:
        return db.jobs.find_one({"paper_id": paper_id}, {"_id": 0})

    def update_job(self, paper_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        updates["updated_at"] = _ts()
        return db.jobs.find_one_and_update(
            {"paper_id": paper_id},
            {"$set": updates},
            projection={"_id": 0},
            return_document=ReturnDocument.AFTER,
        )

    def push_audit(self, paper_id: str, stage: str, event_type: str, payload: dict[str, Any]) -> None:
        event = {
            "event_time": _ts(),
            "paper_id": paper_id,
            "stage": stage,
            "event_type": event_type,
            "event_payload": payload,
        }
        db.jobs.update_one({"paper_id": paper_id}, {"$push": {"audit": event}, "$set": {"updated_at": _ts()}})

    def upsert_processed_paper(self, paper_id: str, document: dict[str, Any]) -> None:
        db.papers.update_one({"paper_id": paper_id}, {"$set": document}, upsert=True)

    def get_processed_paper(self, paper_id: str) -> dict[str, Any] | None:
        return db.papers.find_one({"paper_id": paper_id}, {"_id": 0})


repo = PaperRepository()
