from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    mongo_uri: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    mongo_db: str = os.getenv("MONGO_DB", "researchbridge")
    upload_dir: str = os.getenv("UPLOAD_DIR", "./data/uploads")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_extract_model: str = os.getenv("OPENAI_EXTRACT_MODEL", "gpt-4o")
    openai_verify_model: str = os.getenv("OPENAI_VERIFY_MODEL", "gpt-4o-mini")
    openai_chat_model: str = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    text_density_threshold: int = int(os.getenv("TEXT_DENSITY_THRESHOLD", "80"))


settings = Settings()
