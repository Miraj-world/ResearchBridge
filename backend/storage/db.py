from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

try:
    from pymongo import MongoClient
    from pymongo.collection import Collection
    from pymongo.errors import PyMongoError
except Exception:  # pragma: no cover - optional dependency fallback
    MongoClient = None  # type: ignore[assignment]
    Collection = Any  # type: ignore[assignment]

    class PyMongoError(Exception):
        pass

from backend.models.schemas import JobRecord, PaperListItem, ProcessedPaper, StorageWriteResult


class StorageService:
    def __init__(self, mongodb_uri: str, db_name: str, json_dir: str) -> None:
        self._mongodb_uri = mongodb_uri
        self._db_name = db_name
        self._json_dir = Path(json_dir)
        self._json_dir.mkdir(parents=True, exist_ok=True)

        self._client: Any = None
        self._db = None

    def connect(self) -> None:
        if MongoClient is None:
            self._client = None
            self._db = None
            return
        try:
            self._client = MongoClient(self._mongodb_uri, serverSelectionTimeoutMS=3000)
            self._client.server_info()
            self._db = self._client[self._db_name]
        except Exception:
            self._client = None
            self._db = None

    @property
    def jobs(self) -> Collection | None:
        return self._db["jobs"] if self._db is not None else None

    @property
    def papers(self) -> Collection | None:
        return self._db["processed_papers"] if self._db is not None else None

    def _paper_json_path(self, paper_id: UUID) -> Path:
        return self._json_dir / f"{paper_id}.json"

    def _job_json_path(self, paper_id: UUID) -> Path:
        return self._json_dir / f"{paper_id}.job.json"

    def save_job(self, job: JobRecord) -> None:
        payload = job.model_dump(mode="json")
        if self.jobs is not None:
            try:
                self.jobs.update_one({"paper_id": str(job.paper_id)}, {"$set": payload}, upsert=True)
                return
            except PyMongoError:
                pass
        self._job_json_path(job.paper_id).write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    def get_job(self, paper_id: UUID) -> JobRecord | None:
        if self.jobs is not None:
            doc = self.jobs.find_one({"paper_id": str(paper_id)})
            if doc:
                doc.pop("_id", None)
                return JobRecord.model_validate(doc)

        path = self._job_json_path(paper_id)
        if path.exists():
            return JobRecord.model_validate_json(path.read_text(encoding="utf-8"))
        return None

    def save_processed_paper(self, paper: ProcessedPaper) -> StorageWriteResult:
        payload = paper.model_dump(mode="json")
        if self.papers is not None:
            try:
                self.papers.update_one({"paper_id": str(paper.paper_id)}, {"$set": payload}, upsert=True)
                return StorageWriteResult(stored_in="mongodb")
            except PyMongoError:
                pass

        path = self._paper_json_path(paper.paper_id)
        path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
        return StorageWriteResult(stored_in="json", path=str(path))

    def get_processed_paper(self, paper_id: UUID) -> ProcessedPaper | None:
        if self.papers is not None:
            doc = self.papers.find_one({"paper_id": str(paper_id)})
            if doc:
                doc.pop("_id", None)
                return ProcessedPaper.model_validate(doc)

        path = self._paper_json_path(paper_id)
        if path.exists():
            return ProcessedPaper.model_validate_json(path.read_text(encoding="utf-8"))
        return None

    def list_papers(self) -> list[PaperListItem]:
        output: list[PaperListItem] = []
        seen: set[str] = set()

        if self.papers is not None:
            for doc in self.papers.find({}, {"paper_id": 1, "title": 1, "processed_at": 1}):
                doc.pop("_id", None)
                output.append(PaperListItem.model_validate(doc))
                seen.add(str(doc.get("paper_id", "")))

        for path in self._json_dir.glob("*.json"):
            if path.name.endswith(".job.json"):
                continue
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                paper_id = str(raw.get("paper_id", ""))
                if not paper_id or paper_id in seen:
                    continue
                output.append(
                    PaperListItem(
                        paper_id=UUID(paper_id),
                        title=str(raw.get("title", "Untitled")),
                        processed_at=str(raw.get("processed_at", "")),
                    )
                )
            except Exception:
                continue

        output.sort(key=lambda p: p.processed_at, reverse=True)
        return output
