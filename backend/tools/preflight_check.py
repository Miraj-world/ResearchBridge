from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from shutil import which


def find_tesseract() -> str | None:
    on_path = which("tesseract")
    if on_path:
        return on_path

    candidates = [
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def main() -> int:
    required_modules = ["docling", "fitz", "pytesseract"]
    missing_modules = [name for name in required_modules if importlib.util.find_spec(name) is None]
    tesseract_path = find_tesseract()
    missing_tesseract = tesseract_path is None

    if not missing_modules and not missing_tesseract:
        print("[Backend Preflight] All PDF extraction dependencies are available.")
        print(f"[Backend Preflight] Tesseract: {tesseract_path}")
        return 0

    print("[Backend Preflight] Missing dependencies detected:")
    for module_name in missing_modules:
        print(f"  - Python module missing: {module_name}")
    if missing_tesseract:
        print("  - Tesseract executable missing from PATH")
    else:
        print(f"  - Tesseract found at: {tesseract_path}")

    print("\nInstall commands:")
    print("  pip install -r backend/requirements.txt")
    print("  pip install docling pymupdf pytesseract")
    print("\nTesseract install (Windows):")
    print("  1) Install Tesseract OCR (for example: 'winget install UB-Mannheim.TesseractOCR')")
    print("  2) Ensure tesseract.exe is in PATH")
    print("  3) Verify with: tesseract --version")

    return 1


if __name__ == "__main__":
    sys.exit(main())
