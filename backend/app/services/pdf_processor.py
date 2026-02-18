"""PDF processing: text extraction, OCR, layout analysis."""
import io
import logging
from pathlib import Path
from typing import Tuple, List, Dict, Optional
import pdfplumber
from PIL import Image

logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    fitz = None

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

# Common domain columns - configurable
DEFAULT_DOMAIN_COLUMNS = [
    "document_title", "date", "author", "subject", "company_name",
    "invoice_number", "amount", "description", "keywords",
    "section_1", "section_2", "section_3", "raw_text_preview"
]


def extract_text_pdfplumber(pdf_path: Path) -> Tuple[str, List[Dict]]:
    """Extract text and tables using pdfplumber (best for digital PDFs)."""
    full_text = []
    tables_data = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text.append(text)
            # Extract tables
            tables = page.extract_tables()
            for table in tables:
                if table:
                    tables_data.append({"rows": table})
    return "\n\n".join(full_text) if full_text else "", tables_data


def extract_text_pymupdf(pdf_path: Path) -> str:
    """Extract text using PyMuPDF (fallback, good for some PDFs)."""
    if not PYMUPDF_AVAILABLE:
        return ""
    doc = fitz.open(pdf_path)
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n\n".join(text_parts)


def pdf_to_images(pdf_path: Path, dpi: int = 200) -> List[Image.Image]:
    """Convert PDF pages to images for OCR."""
    if not PYMUPDF_AVAILABLE:
        return []
    doc = fitz.open(pdf_path)
    images = []
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)
    doc.close()
    return images


def ocr_images(images: List[Image.Image]) -> str:
    """Run Tesseract OCR on images."""
    if not TESSERACT_AVAILABLE:
        logger.warning("Tesseract not available; OCR skipped")
        return ""
    texts = []
    for img in images:
        try:
            text = pytesseract.image_to_string(img)
            texts.append(text or "")
        except Exception as e:
            logger.warning(f"OCR failed for image: {e}")
            texts.append("")
    return "\n\n".join(texts)


def detect_if_scanned(pdf_path: Path) -> bool:
    """Heuristic: if pdfplumber extracts very little text, likely scanned."""
    try:
        text_plumber, _ = extract_text_pdfplumber(pdf_path)
        text_pymupdf = extract_text_pymupdf(pdf_path)
        total_chars = max(len(text_plumber), len(text_pymupdf))
        with pdfplumber.open(pdf_path) as pdf:
            page_count = len(pdf.pages)
        # Less than ~50 chars per page suggests scanned
        if page_count > 0 and total_chars / page_count < 50:
            return True
    except Exception:
        pass
    return False


def extract_full_text(pdf_path: Path) -> Tuple[str, bool]:
    """
    Extract all text from PDF.
    Uses pdfplumber first, falls back to OCR for scanned PDFs.
    Returns (text, is_scanned).
    """
    is_scanned = detect_if_scanned(pdf_path)
    text_plumber, tables = extract_text_pdfplumber(pdf_path)
    text_pymupdf = extract_text_pymupdf(pdf_path)
    text = text_plumber or text_pymupdf
    if is_scanned or (text and len(text.strip()) < 100):
        images = pdf_to_images(pdf_path)
        ocr_text = ocr_images(images)
        if ocr_text.strip():
            text = ocr_text
            is_scanned = True
    # Append table content as structured text
    for t in tables:
        for row in t.get("rows", []):
            text += "\n" + " | ".join(str(c) if c else "" for c in row)
    return (text or "").strip(), is_scanned
