from __future__ import annotations

import logging
from pathlib import Path

from backend.models.schemas import IngestionResult


USER_FACING_EXTRACTION_ERROR = "Could not extract text from this PDF. It may be corrupted or image-only."

logger = logging.getLogger("researchbridge.ingestion")


class IngestionError(RuntimeError):
    def __init__(self, message: str, *, docling_error: str | None = None, ocr_error: str | None = None) -> None:
        super().__init__(message)
        self.user_message = message
        self.docling_error = docling_error
        self.ocr_error = ocr_error

    def actionable_error_message(self) -> str:
        issues: list[str] = []
        combined = f"{self.docling_error or ''}\n{self.ocr_error or ''}".lower()

        if "no module named 'docling'" in combined:
            issues.append("Docling is not installed in the current Python environment")
        if "no module named 'fitz'" in combined:
            issues.append("PyMuPDF (fitz) is not installed in the current Python environment")
        if "no module named 'pytesseract'" in combined:
            issues.append("pytesseract is not installed in the current Python environment")
        if "tesseract is not installed" in combined or "not in your path" in combined:
            issues.append("Tesseract executable is not found on PATH")

        if not issues:
            return self.user_message

        return f"{self.user_message} Missing dependency: {'; '.join(issues)}."



def _docling_markdown(file_path: Path) -> str:
    from docling.document_converter import DocumentConverter

    converter = DocumentConverter()
    result = converter.convert(str(file_path))
    return result.document.export_to_markdown().strip()



def _ocr_markdown(file_path: Path) -> str:
    import fitz
    import pytesseract
    from PIL import Image

    markdown_sections: list[str] = []
    doc = fitz.open(str(file_path))
    try:
        scale = 300.0 / 72.0
        matrix = fitz.Matrix(scale, scale)
        for page_index in range(doc.page_count):
            page = doc.load_page(page_index)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            mode = "RGB" if pix.n >= 3 else "L"
            image = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
            text = pytesseract.image_to_string(image).strip()
            if text:
                markdown_sections.append(f"## OCR Page {page_index + 1}\n{text}\n")
    finally:
        doc.close()

    return "\n".join(markdown_sections).strip()



def ingest_pdf(file_path: str) -> IngestionResult:
    path = Path(file_path)
    if not path.exists() or path.suffix.lower() != ".pdf":
        raise ValueError("Invalid PDF file path")

    docling_error: str | None = None
    ocr_error: str | None = None

    try:
        markdown = _docling_markdown(path)
        if markdown:
            return IngestionResult(markdown=markdown, parser_used="docling")
    except Exception as exc:
        docling_error = f"{type(exc).__name__}: {exc}"
        logger.exception("Docling extraction failed for %s", path)

    try:
        markdown = _ocr_markdown(path)
        if markdown:
            return IngestionResult(markdown=markdown, parser_used="pytesseract_300dpi")
    except Exception as exc:
        ocr_error = f"{type(exc).__name__}: {exc}"
        logger.exception("OCR fallback failed for %s", path)

    logger.error(
        "PDF ingestion failed for %s | docling_error=%s | ocr_error=%s",
        path,
        docling_error or "none",
        ocr_error or "none",
    )
    raise IngestionError(
        USER_FACING_EXTRACTION_ERROR,
        docling_error=docling_error,
        ocr_error=ocr_error,
    )
