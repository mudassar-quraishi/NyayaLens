"""
Ingestor agent — handles PDF, DOCX, image (OCR), and pasted text.

Extracts raw text from uploaded files and computes content hash.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path

from app.llm import compute_content_hash

logger = logging.getLogger("nyayalens.ingestor")


async def extract_text(
    file_bytes: bytes,
    filename: str,
    content_type: str | None = None,
) -> tuple[str, str]:
    """
    Extract raw text from a file.

    Returns:
        (raw_text, content_hash)
    """
    ext = Path(filename).suffix.lower()

    if ext == ".pdf" or (content_type and "pdf" in content_type):
        text = _extract_pdf(file_bytes)
        if len(text.strip()) < 50:
            # Possibly a scanned PDF — try OCR
            logger.info("PDF text too short, attempting OCR fallback for %s", filename)
            text = _ocr_pdf(file_bytes)
    elif ext == ".docx" or (content_type and "wordprocessing" in (content_type or "")):
        text = _extract_docx(file_bytes)
    elif ext in (".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp") or (
        content_type and content_type.startswith("image/")
    ):
        text = _ocr_image(file_bytes)
    elif ext == ".txt" or (content_type and "text" in (content_type or "")):
        text = file_bytes.decode("utf-8", errors="replace")
    else:
        # Try as text
        text = file_bytes.decode("utf-8", errors="replace")

    text = text.strip()
    if not text:
        raise ValueError(f"Could not extract text from {filename}")

    content_hash = compute_content_hash(text)
    logger.info("Extracted %d chars from %s (hash=%s)", len(text), filename, content_hash)
    return text, content_hash


def _extract_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF using PyMuPDF."""
    import fitz  # PyMuPDF

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return "\n\n".join(pages)


def _ocr_pdf(file_bytes: bytes) -> str:
    """OCR a scanned PDF by rendering pages to images."""
    import fitz
    from PIL import Image
    import pytesseract

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    texts = []
    for page in doc:
        pix = page.get_pixmap(dpi=300)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        text = pytesseract.image_to_string(img, lang="eng+hin")
        texts.append(text)
    doc.close()
    return "\n\n".join(texts)


def _ocr_image(file_bytes: bytes) -> str:
    """OCR an image file."""
    from PIL import Image
    import pytesseract

    img = Image.open(io.BytesIO(file_bytes))
    return pytesseract.image_to_string(img, lang="eng+hin")


def _extract_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX."""
    from docx import Document

    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)
