"""Extraction models."""
from pydantic import BaseModel
from typing import Any, Dict, List, Optional


class DomainField(BaseModel):
    """Single extracted field with confidence."""
    name: str
    value: Any
    confidence: float = 1.0
    section: Optional[str] = None
    raw_text: Optional[str] = None


class ExtractionResult(BaseModel):
    """Extraction result for one PDF."""
    file_name: str
    file_path: str
    fields: Dict[str, Any]
    confidence_scores: Dict[str, float] = {}
    sections_detected: List[str] = []
    is_scanned: bool = False
    error: Optional[str] = None
