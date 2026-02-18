"""Orchestrates PDF processing and AI extraction for batch jobs."""
import logging
from pathlib import Path
from typing import List, Dict, Any, Callable, Optional

from app.services.pdf_processor import extract_full_text, DEFAULT_DOMAIN_COLUMNS
from app.services.ai_extractor import extract_with_openai, extract_rule_based
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def process_single_pdf(
    pdf_path: Path,
    domain_columns: Optional[List[str]] = None,
    on_progress: Optional[Callable[[int, int, str], None]] = None
) -> Dict[str, Any]:
    """
    Process one PDF: extract text (with OCR if scanned), run AI extraction.
    """
    cols = domain_columns or DEFAULT_DOMAIN_COLUMNS
    try:
        text, is_scanned = extract_full_text(pdf_path)
        if not text:
            return {
                "file_name": pdf_path.name,
                "file_path": str(pdf_path),
                "fields": {c: None for c in cols},
                "confidence_scores": {},
                "sections_detected": [],
                "is_scanned": is_scanned,
                "error": "No text could be extracted"
            }
        api_key = getattr(settings, "openai_api_key", "") or ""
        result = extract_with_openai(text, cols, api_key)
        fields = result.get("fields", {})
        scores = result.get("confidence_scores", {})
        # Ensure all columns present
        for c in cols:
            if c not in fields:
                fields[c] = None
            if c not in scores:
                scores[c] = 0.0
        return {
            "file_name": pdf_path.name,
            "file_path": str(pdf_path),
            "fields": fields,
            "confidence_scores": scores,
            "sections_detected": result.get("sections", []),
            "is_scanned": is_scanned,
            "error": None
        }
    except Exception as e:
        logger.exception(f"Error processing {pdf_path}")
        return {
            "file_name": pdf_path.name,
            "file_path": str(pdf_path),
            "fields": {},
            "confidence_scores": {},
            "sections_detected": [],
            "is_scanned": False,
            "error": str(e)
        }


def process_batch(
    pdf_paths: List[Path],
    domain_columns: Optional[List[str]] = None,
    on_progress: Optional[Callable[[int, int, str], None]] = None
) -> List[Dict[str, Any]]:
    """Process multiple PDFs and return extraction results."""
    results = []
    total = len(pdf_paths)
    for i, p in enumerate(pdf_paths):
        if on_progress:
            on_progress(i + 1, total, p.name)
        r = process_single_pdf(p, domain_columns, on_progress)
        results.append(r)
    return results
