"""Orchestrates PDF processing and extraction using traditional methods."""
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Callable, Optional

from app.services.pdf_processor import extract_full_text

logger = logging.getLogger(__name__)


def extract_fields_traditional(text: str) -> Dict[str, Any]:
    """Extract fields using traditional rule-based methods - no AI."""
    fields = {}
    confidence_scores = {}
    sections = []
    
    lines = text.split("\n")
    
    # Pattern 1: Detect sections (short lines, uppercase, or ending with colon)
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped or len(line_stripped) > 100:
            continue
        if line.isupper() or line.endswith(":") or (len(line_stripped) < 50 and line_stripped and line_stripped[0].isupper()):
            sections.append(line_stripped.rstrip(":"))
    
    # Pattern 2: Extract label-value pairs with separators (:, -, =)
    separators = [':', '-', '=', '–', '—']
    for line in lines:
        text_line = line.strip()
        if not text_line or len(text_line) > 200:
            continue
        
        for sep in separators:
            if sep in text_line:
                parts = text_line.split(sep, 1)
                if len(parts) == 2:
                    label = parts[0].strip()
                    value = parts[1].strip()
                    
                    # Clean label
                    label = re.sub(r'[^\w\s]', '', label).strip().lower()
                    label = label.replace(' ', '_')
                    
                    if label and value and len(label) < 50 and len(value) > 0:
                        fields[label] = value
                        confidence_scores[label] = 0.8
                        break
    
    # Pattern 3: Extract common field patterns without separators
    # Look for keywords followed by values
    field_patterns = [
        (r'(?:employee|emp)\s*name\s*[:\s]*(.+)', 'employee_name'),
        (r'(?:employer|company)\s*[:\s]*(.+)', 'employer'),
        (r'(?:month|period)\s*[:\s]*(.+)', 'month'),
        (r'gross\s*(?:salary|pay)?\s*[:\s]*(.+)', 'gross_salary'),
        (r'net\s*(?:salary|pay)?\s*[:\s]*(.+)', 'net_salary'),
        (r'basic\s*(?:salary|pay)?\s*[:\s]*(.+)', 'basic_salary'),
        (r'designation\s*[:\s]*(.+)', 'designation'),
        (r'department\s*[:\s]*(.+)', 'department'),
        (r'(?:id|emp\s*id|employee\s*id)\s*[:\s]*(.+)', 'employee_id'),
        (r'pan\s*(?:no|number)?\s*[:\s]*(.+)', 'pan_number'),
        (r'date\s*[:\s]*(.+)', 'date'),
        (r'invoice\s*(?:no|number|#)?\s*[:\s]*(.+)', 'invoice_number'),
        (r'amount\s*[:\s]*(.+)', 'amount'),
        (r'total\s*[:\s]*(.+)', 'total'),
        (r'email\s*[:\s]*(.+)', 'email'),
        (r'phone\s*(?:no|number)?\s*[:\s]*(.+)', 'phone'),
        (r'address\s*[:\s]*(.+)', 'address'),
    ]
    
    for line in lines:
        line_lower = line.lower().strip()
        for pattern, field_name in field_patterns:
            match = re.search(pattern, line_lower)
            if match:
                value = match.group(1).strip()
                if value and field_name not in fields:
                    fields[field_name] = value
                    confidence_scores[field_name] = 0.75
                    break
    
    return {
        "fields": fields,
        "confidence_scores": confidence_scores,
        "sections": sections
    }


def process_single_pdf(
    pdf_path: Path,
    on_progress: Optional[Callable[[int, int, str], None]] = None
) -> Dict[str, Any]:
    """
    Process one PDF: extract text (with OCR if scanned), run traditional extraction.
    Uses rule-based methods only - no AI required.
    """
    try:
        text, is_scanned = extract_full_text(pdf_path)
        if not text:
            return {
                "file_name": pdf_path.name,
                "fields": {}
            }
        
        # Use traditional extraction - no AI
        result = extract_fields_traditional(text)
        fields = result.get("fields", {})
        scores = result.get("confidence_scores", {})
        
        # Return only the extracted fields, no extra metadata
        return {
            "file_name": pdf_path.name,
            "fields": fields
        }
    except Exception as e:
        logger.exception(f"Error processing {pdf_path}")
        return {
            "file_name": pdf_path.name,
            "fields": {}
        }


def process_batch(
    pdf_paths: List[Path],
    on_progress: Optional[Callable[[int, int, str], None]] = None
) -> List[Dict[str, Any]]:
    """Process multiple PDFs and return extraction results."""
    results = []
    total = len(pdf_paths)
    for i, p in enumerate(pdf_paths):
        if on_progress:
            on_progress(i + 1, total, p.name)
        r = process_single_pdf(p, on_progress)
        results.append(r)
    return results
