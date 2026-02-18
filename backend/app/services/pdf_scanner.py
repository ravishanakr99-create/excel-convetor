"""Simple PDF scanner - extracts ALL content from PDFs without hard-coded formats."""
import io
import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

import pdfplumber
import pandas as pd

logger = logging.getLogger(__name__)


def extract_all_text(pdf_path: Path) -> str:
    """Extract all text from PDF - no filtering, no hard-coded patterns."""
    all_text = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    all_text.append(text)
    except Exception as e:
        logger.error(f"Error reading {pdf_path}: {e}")
        return ""
    
    return "\n\n".join(all_text)


def extract_text_with_layout(pdf_path: Path) -> List[Dict[str, Any]]:
    """Extract text with position info - each line as a row."""
    lines = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                words = page.extract_words(
                    keep_blank_chars=True,
                    x_tolerance=3,
                    y_tolerance=3
                )
                
                # Group words by line (y-position)
                line_groups = defaultdict(list)
                for word in words:
                    # Round y position to group nearby words
                    y_key = round(word["top"] / 5) * 5
                    line_groups[y_key].append(word)
                
                # Sort lines top to bottom
                for y_pos in sorted(line_groups.keys()):
                    line_words = sorted(line_groups[y_pos], key=lambda w: w["x0"])
                    text = " ".join(w["text"] for w in line_words).strip()
                    if text:
                        lines.append({
                            "page": page_num + 1,
                            "y_position": y_pos,
                            "text": text
                        })
    except Exception as e:
        logger.error(f"Error extracting layout from {pdf_path}: {e}")
    
    return lines


def detect_label_value_pairs(lines: List[Dict[str, Any]]) -> Dict[str, str]:
    """Detect label-value pairs from lines - flexible matching."""
    fields = {}
    
    for i, line in enumerate(lines):
        text = line["text"]
        
        # Look for separator patterns (:, -, =)
        separators = [':', '-', '=', '–', '—']
        for sep in separators:
            if sep in text and text.count(sep) == 1:
                parts = text.split(sep, 1)
                if len(parts) == 2:
                    label = parts[0].strip()
                    value = parts[1].strip()
                    
                    # Clean up label
                    label = re.sub(r'[^\w\s]', '', label).strip().lower()
                    label = label.replace(' ', '_')
                    
                    if label and value and len(label) < 50:
                        fields[label] = value
                        break
    
    return fields


def scan_pdf(pdf_path: Path) -> Dict[str, Any]:
    """Scan a single PDF and extract all fields."""
    logger.info(f"Scanning: {pdf_path.name}")
    
    # Extract all content
    full_text = extract_all_text(pdf_path)
    lines = extract_text_with_layout(pdf_path)
    fields = detect_label_value_pairs(lines)
    
    # If no fields detected with separators, use line-based extraction
    if not fields and lines:
        for i, line in enumerate(lines[:20]):  # First 20 lines
            text = line["text"].strip()
            if text and len(text) < 100:
                fields[f"field_{i+1}"] = text
    
    return {
        "file_name": pdf_path.name,
        "fields": fields,
        "raw_text": full_text[:2000],  # First 2000 chars for preview
        "total_lines": len(lines)
    }


def scan_multiple_pdfs(pdf_paths: List[Path]) -> List[Dict[str, Any]]:
    """Scan multiple PDFs and collect all fields."""
    results = []
    all_field_names = set()
    
    for pdf_path in pdf_paths:
        result = scan_pdf(pdf_path)
        results.append(result)
        all_field_names.update(result["fields"].keys())
    
    # Normalize: ensure all results have same fields
    for result in results:
        for field_name in all_field_names:
            if field_name not in result["fields"]:
                result["fields"][field_name] = ""
    
    return results


def create_excel_from_scans(results: List[Dict[str, Any]]) -> bytes:
    """Create Excel file from scanned PDF results."""
    if not results:
        # Empty Excel
        df = pd.DataFrame(columns=["file_name"])
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False, sheet_name="Scanned Data")
        buffer.seek(0)
        return buffer.getvalue()
    
    # Build rows
    rows = []
    for result in results:
        row = {"file_name": result["file_name"]}
        row.update(result["fields"])
        rows.append(row)
    
    # Create DataFrame
    df = pd.DataFrame(rows)
    
    # Ensure file_name is first column
    cols = ["file_name"] + [c for c in df.columns if c != "file_name"]
    df = df[cols]
    
    # Write to Excel
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Scanned Data")
        
        # Format header
        sheet = writer.sheets["Scanned Data"]
        for cell in sheet[1]:
            cell.font = cell.font.copy(bold=True)
    
    buffer.seek(0)
    return buffer.getvalue()


def scan_zip_and_create_excel(zip_path: Path) -> Tuple[bytes, List[Dict[str, Any]]]:
    """Extract ZIP, scan all PDFs, create Excel."""
    import zipfile
    import tempfile
    import shutil
    
    pdf_files = []
    results = []
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Extract ZIP
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for member in zf.namelist():
                if member.lower().endswith('.pdf'):
                    zf.extract(member, temp_path)
                    extracted = temp_path / member
                    if extracted.exists():
                        # Flatten path
                        flat_name = member.replace('/', '_').replace('\\', '_')
                        flat_path = temp_path / flat_name
                        shutil.move(str(extracted), str(flat_path))
                        pdf_files.append(flat_path)
        
        # Scan all PDFs
        pdf_files.sort()
        results = scan_multiple_pdfs(pdf_files)
        
        # Create Excel
        excel_bytes = create_excel_from_scans(results)
        
        return excel_bytes, results
