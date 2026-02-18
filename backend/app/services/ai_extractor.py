"""AI-based extraction using LLM for section detection and field extraction."""
import json
import logging
import re
from typing import Dict, List, Any, Optional
from app.services.pdf_processor import DEFAULT_DOMAIN_COLUMNS

logger = logging.getLogger(__name__)

# Try OpenAI, fallback to rule-based if no API key
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


def extract_with_openai(text: str, domain_columns: List[str], api_key: str) -> Dict[str, Any]:
    """Use OpenAI to extract structured data from PDF text."""
    if not api_key or not OPENAI_AVAILABLE:
        return extract_rule_based(text, domain_columns)
    client = OpenAI(api_key=api_key)
    columns_str = ", ".join(domain_columns)
    prompt = f"""You are a document data extraction assistant. Extract structured data from the following document text.
Output a JSON object with keys from this list (use only those that apply): {columns_str}
For each key, provide the extracted value. Use null for missing values.
Also add "confidence_scores" object with 0-1 score per field.
Extract dates, numbers, names, titles, amounts, descriptions etc. based on context.
Be consistent: if you see "Invoice #: 123", use invoice_number: "123".
Return ONLY valid JSON, no markdown or extra text."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You extract structured data from documents. Output only valid JSON."},
                {"role": "user", "content": f"{prompt}\n\n--- Document text ---\n{text[:12000]}"}
            ],
            temperature=0.1,
        )
        content = response.choices[0].message.content
        content = re.sub(r"^```\w*\n?", "", content)
        content = re.sub(r"\n?```$", "", content)
        data = json.loads(content.strip())
        confidence = data.pop("confidence_scores", {})
        return {"fields": data, "confidence_scores": confidence, "sections": list(data.keys())}
    except Exception as e:
        logger.warning(f"OpenAI extraction failed: {e}")
        return extract_rule_based(text, domain_columns)


def extract_rule_based(text: str, domain_columns: List[str]) -> Dict[str, Any]:
    """Rule-based and regex extraction when LLM is unavailable."""
    fields = {}
    confidence_scores = {}
    sections = []

    # Common patterns
    patterns = {
        "date": r"\b\d{1,4}[-/]\d{1,2}[-/]\d{1,4}\b|\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{2,4}\b",
        "invoice_number": r"(?:invoice|inv)\s*#?\s*:?\s*([A-Z0-9\-]+)",
        "amount": r"(?:amount|total|sum)\s*:?\s*\$?\s*([\d,]+\.?\d*)",
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "phone": r"\+?\d[\d\s\-()]{7,}",
    }

    lines = text.split("\n")
    for i, line in enumerate(lines):
        line_lower = line.lower().strip()
        if not line_lower:
            continue
        # Section headings (short lines, often all caps or end with :)
        if len(line) < 80 and (line.isupper() or line.endswith(":")):
            sections.append(line.strip(":").strip())
        for col in domain_columns:
            if col in patterns:
                m = re.search(patterns[col], line, re.I)
                if m:
                    val = m.group(1) if m.lastindex else m.group(0)
                    if col not in fields:
                        fields[col] = val
                        confidence_scores[col] = 0.85

    # Title: first non-empty line
    if "document_title" in domain_columns and "document_title" not in fields:
        for line in lines:
            if len(line.strip()) > 3 and len(line) < 150:
                fields["document_title"] = line.strip()
                confidence_scores["document_title"] = 0.7
                break

    # Raw text preview
    if "raw_text_preview" in domain_columns:
        fields["raw_text_preview"] = text[:500].replace("\n", " ") if text else ""
        confidence_scores["raw_text_preview"] = 1.0

    # Fill missing with empty
    for col in domain_columns:
        if col not in fields:
            fields[col] = None
            confidence_scores[col] = 0.0

    return {"fields": fields, "confidence_scores": confidence_scores, "sections": sections}
