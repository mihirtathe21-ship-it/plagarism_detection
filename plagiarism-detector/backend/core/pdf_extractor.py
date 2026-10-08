import io
import re
from typing import Tuple

try:
    from pypdf import PdfReader
    PDF_AVAILABLE = True
except ImportError:
    PdfReader = None
    PDF_AVAILABLE = False


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> Tuple[str, dict]:
    """Extract text from a PDF file as a plain string."""
    if not PDF_AVAILABLE or PdfReader is None:
        return "", {"error": "pypdf not installed", "success": False}

    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages = []
        for page in reader.pages:
            text = page.extract_text() or ""
            pages.append(text)
        combined = "\n\n".join(pages).strip()
        metadata = reader.metadata or {}
        title = str(metadata.get("/Title") or "").strip()
        return combined, {
            "success": bool(combined),
            "page_count": len(reader.pages),
            "extractor": "pypdf",
            "word_count": len(combined.split()),
            "title": re.sub(r"\s+", " ", title) if title else "",
        }
    except Exception as exc:
        return "", {"error": str(exc), "success": False}
