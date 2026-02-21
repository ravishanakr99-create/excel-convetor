"""AI-based extraction using LLM for section detection and field extraction."""
import json
import logging
import re
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Try OpenAI, fallback to rule-based if no API key
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


def extract_with_openai(text: str, api_key: str) -> Dict[str, Any]:
    """Use OpenAI to extract structured data from PDF text with automatic section detection."""
    if not api_key or not OPENAI_AVAILABLE:
        return extract_rule_based(text)
    
    client = OpenAI(api_key=api_key)
    
    prompt = """You are an intelligent document analyzer. Your task is to:

1. Identify all logical sections in the document
2. Detect section headings automatically
3. Extract ALL fields with their exact values
4. Group fields under their correct sections
5. Normalize similar labels (e.g., "PAN", "Pan No", "Permanent Account Number" → "pan")
6. Do NOT guess - only extract what is explicitly present
7. Preserve original values exactly as they appear

Return format:
{
  "sections": [
    {
      "section_name": "Section Name",
      "fields": {
        "field_name": "field_value",
        "another_field": "another_value"
      }
    }
  ]
}

Rules:
- Create sections based on document structure (headers, bold text, separators)
- If no clear sections, group related fields logically
- Use lowercase with underscores for field names
- Return empty sections array if no structure detected
- Return only valid JSON, no markdown, no explanations

Now analyze this document:"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You analyze documents and extract structured data. Output only valid JSON."},
                {"role": "user", "content": f"{prompt}\n\n{text[:12000]}"}
            ],
            temperature=0.1,
        )
        content = response.choices[0].message.content
        content = re.sub(r"^```\w*\n?", "", content)
        content = re.sub(r"\n?```$", "", content)
        data = json.loads(content.strip())
        
        # Convert sections to flat fields while preserving section info
        fields = {}
        confidence_scores = {}
        section_names = []
        
        for section in data.get("sections", []):
            section_name = section.get("section_name", "")
            if section_name:
                section_names.append(section_name)
            
            for field_name, field_value in section.get("fields", {}).items():
                if field_value is not None and field_value != "":
                    fields[field_name] = field_value
                    confidence_scores[field_name] = 0.95
        
        return {
            "fields": fields,
            "confidence_scores": confidence_scores,
            "sections": section_names
        }
    except Exception as e:
        logger.warning(f"OpenAI extraction failed: {e}")
        return extract_rule_based(text)


def extract_rule_based(text: str) -> Dict[str, Any]:
    """Rule-based extraction - discovers fields automatically from document structure."""
    fields = {}
    confidence_scores = {}
    sections = []

    lines = text.split("\n")
    
    # Detect sections (lines that are short, uppercase, or end with colon)
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped or len(line_stripped) > 100:
            continue
        if line.isupper() or line.endswith(":") or (len(line_stripped) < 50 and line_stripped and line_stripped[0].isupper()):
            sections.append(line_stripped.rstrip(":"))
    
    # Extract key-value pairs (Label: Value or Label - Value)
    kv_pattern = r'^([A-Za-z][A-Za-z\s]+?)[\s]*[:|-][\s]*(.+)$'
    for line in lines:
        line_stripped = line.strip()
        match = re.match(kv_pattern, line_stripped)
        if match:
            key = match.group(1).strip().lower().replace(" ", "_")
            value = match.group(2).strip()
            if key and value and len(key) < 50 and len(value) > 0:
                fields[key] = value
                confidence_scores[key] = 0.75

    return {"fields": fields, "confidence_scores": confidence_scores, "sections": sections}
