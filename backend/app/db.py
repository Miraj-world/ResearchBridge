from __future__ import annotations

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from .config import settings


class DatabaseManager:
    def __init__(self) -> None:
        self.client: MongoClient | None = None
        self.db: Database | None = None

    def connect(self) -> None:
        self.client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=3000)
        self.client.admin.command("ping")
        self.db = self.client[settings.mongo_db]
        self._init_indexes()

    def _init_indexes(self) -> None:
        assert self.db is not None
        self.jobs.create_index("paper_id", unique=True)
        self.papers.create_index("paper_id", unique=True)
        self.jobs.create_index("processing.state")

    @property
    def jobs(self) -> Collection:
        if self.db is None:
            raise RuntimeError("Database is not initialized")
        return self.db["paper_jobs"]

    @property
    def papers(self) -> Collection:
        if self.db is None:
            raise RuntimeError("Database is not initialized")
        return self.db["processed_papers"]

    def close(self) -> None:
        if self.client is not None:
            self.client.close()


db = DatabaseManager()
