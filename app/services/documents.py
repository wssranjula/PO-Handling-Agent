from pathlib import Path

from pypdf import PdfReader


def extract_text(path: Path, content_type: str) -> str:
    if content_type == "application/pdf" or path.suffix.lower() == ".pdf":
        reader = PdfReader(path)
        return "\n\n".join(page.extract_text() or "" for page in reader.pages).strip()

    if content_type.startswith("text/") or path.suffix.lower() in {".txt", ".csv"}:
        return path.read_text(encoding="utf-8", errors="replace")

    raise ValueError(f"Unsupported attachment type: {content_type}")
