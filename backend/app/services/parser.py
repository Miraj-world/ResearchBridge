from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

from ..config import settings


@dataclass
class ParseResult:
    markdown: str
    parser_path: str
    timings_ms: dict[str, int]


def _text_density(text: str) -> int:
    alnum_count = sum(1 for c in text if c.isalnum())
    return alnum_count


def _has_markdown_headers(text: str) -> bool:
    return bool(re.search(r"^#{1,6}\s+\S+", text, flags=re.MULTILINE))


def _parse_docling(file_path: str) -> str | None:
    try:
        from docling.document_converter import DocumentConverter  # type: ignore
    except Exception:
        return None

    try:
        converter = DocumentConverter()
        result = converter.convert(file_path)
        if hasattr(result, "document") and hasattr(result.document, "export_to_markdown"):
            md = result.document.export_to_markdown()
            return md if isinstance(md, str) and md.strip() else None
        if hasattr(result, "export_to_markdown"):
            md = result.export_to_markdown()
            return md if isinstance(md, str) and md.strip() else None
    except Exception:
        return None
    return None


def _parse_pymupdf(file_path: str) -> str | None:
    try:
        import fitz  # type: ignore
    except Exception:
        return None

    try:
        chunks: list[str] = []
        doc = fitz.open(file_path)
        for idx, page in enumerate(doc):
            page_text = page.get_text("text") or ""
            chunks.append(f"## Page {idx + 1}\n{page_text.strip()}")
        text = "\n\n".join(chunks).strip()
        return text if text else None
    except Exception:
        return None


def _ocr_fallback(file_path: str) -> str | None:
    try:
        from PIL import Image  # noqa: F401
        import pytesseract  # type: ignore
    except Exception:
        return None

    # Optional dependency chain for PDF rasterization.
    images = None
    try:
        from pdf2image import convert_from_path  # type: ignore

        images = convert_from_path(file_path, dpi=300)
    except Exception:
        images = None

    if not images:
        return None

    text_blocks: list[str] = []
    for idx, image in enumerate(images):
        text = pytesseract.image_to_string(image) or ""
        text_blocks.append(f"## OCR Page {idx + 1}\n{text.strip()}")

    text = "\n\n".join(text_blocks).strip()
    return text if text else None


def parse_pdf_to_markdown(file_path: str) -> ParseResult:
    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)

    timings: dict[str, int] = {}

    t0 = time.perf_counter()
    docling_md = _parse_docling(file_path)
    timings["docling"] = int((time.perf_counter() - t0) * 1000)

    if docling_md:
        density = _text_density(docling_md)
        if density >= settings.text_density_threshold and _has_markdown_headers(docling_md):
            return ParseResult(markdown=docling_md, parser_path="docling_only", timings_ms=timings)

    t1 = time.perf_counter()
    pymupdf_md = _parse_pymupdf(file_path)
    timings["pymupdf"] = int((time.perf_counter() - t1) * 1000)

    if pymupdf_md:
        density = _text_density(pymupdf_md)
        if density >= settings.text_density_threshold:
            parser_path = "docling_plus_pymupdf" if docling_md else "pymupdf_only"
            return ParseResult(markdown=pymupdf_md, parser_path=parser_path, timings_ms=timings)

    t2 = time.perf_counter()
    ocr_md = _ocr_fallback(file_path)
    timings["ocr"] = int((time.perf_counter() - t2) * 1000)
    if ocr_md and _text_density(ocr_md) >= settings.text_density_threshold:
        return ParseResult(markdown=ocr_md, parser_path="docling_plus_ocr", timings_ms=timings)

    raise RuntimeError("PARSER_FAILED")


def ensure_upload_dir(upload_dir: str) -> None:
    Path(upload_dir).mkdir(parents=True, exist_ok=True)
