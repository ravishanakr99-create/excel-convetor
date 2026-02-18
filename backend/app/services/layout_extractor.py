"""Layout-aware PDF extraction with spatial analysis and template learning."""
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict
import hashlib

import pdfplumber
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Try OpenAI for semantic classification
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


@dataclass
class TextBlock:
    """Represents a text element with spatial coordinates."""
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    page: int = 0
    font_size: float = 0.0
    is_bold: bool = False
    block_type: str = "text"  # 'label', 'value', 'header', 'unknown'
    
    @property
    def center_x(self) -> float:
        return (self.x0 + self.x1) / 2
    
    @property
    def center_y(self) -> float:
        return (self.y0 + self.y1) / 2
    
    @property
    def width(self) -> float:
        return self.x1 - self.x0
    
    @property
    def height(self) -> float:
        return self.y1 - self.y0
    
    def distance_to(self, other: 'TextBlock') -> float:
        """Calculate Euclidean distance to another block."""
        return ((self.center_x - other.center_x) ** 2 + 
                (self.center_y - other.center_y) ** 2) ** 0.5
    
    def is_near(self, other: 'TextBlock', threshold: float = 50.0) -> bool:
        """Check if another block is within threshold distance."""
        return self.distance_to(other) < threshold


@dataclass
class FieldPattern:
    """Detected field pattern with label-value relationship."""
    label: TextBlock
    value: Optional[TextBlock] = None
    field_type: str = "unknown"
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "label_text": self.label.text,
            "value_text": self.value.text if self.value else None,
            "field_type": self.field_type,
            "confidence": self.confidence,
            "position": {
                "x": self.label.x0,
                "y": self.label.y0,
                "page": self.label.page
            }
        }


@dataclass
class Template:
    """Learned template from multiple PDFs."""
    template_id: str
    field_positions: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    label_patterns: List[str] = field(default_factory=list)
    sample_count: int = 0
    
    def generate_id(self, blocks: List[TextBlock]) -> str:
        """Generate template ID from layout fingerprint."""
        # Create fingerprint from block positions and types
        fingerprint = ""
        for b in sorted(blocks, key=lambda x: (x.page, x.y0, x.x0))[:20]:
            fingerprint += f"{b.page}:{int(b.y0/10)}:{int(b.x0/100)}:{b.block_type[0]}"
        return hashlib.md5(fingerprint.encode()).hexdigest()[:12]


class LayoutAnalyzer:
    """Analyzes PDF layout to detect field patterns."""
    
    # Semantic patterns for label detection (flexible matching)
    LABEL_PATTERNS = {
        "name": [r"name", r"full\s*name", r"customer\s*name", r"applicant\s*name", 
                 r"client\s*name", r"person\s*name", r"contact\s*name"],
        "id_number": [r"id\s*#?", r"id\s*number", r"national\s*id", r"ssn", 
                      r"social\s*security", r"passport", r"license\s*#?", r"id\s*no"],
        "phone": [r"phone", r"telephone", r"mobile", r"cell", r"contact\s*#?", 
                  r"phone\s*#?", r"tel", r"fax"],
        "address": [r"address", r"street", r"location", r"residence", r"home", 
                    r"mailing\s*address", r"current\s*address"],
        "dob": [r"date\s*of\s*birth", r"dob", r"birth\s*date", r"born", r"birthday"],
        "email": [r"e-?mail", r"email\s*address", r"electronic\s*mail"],
    }
    
    def __init__(self):
        self.templates: Dict[str, Template] = {}
        self.current_template: Optional[Template] = None
    
    def extract_blocks(self, pdf_path: Path) -> List[TextBlock]:
        """Extract text blocks with coordinates from PDF."""
        blocks = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # Extract words with their bounding boxes
                    words = page.extract_words(
                        keep_blank_chars=True,
                        x_tolerance=3,
                        y_tolerance=3
                    )
                    
                    # Group words into lines/blocks
                    lines = self._group_words_into_lines(words)
                    
                    for line in lines:
                        if line:
                            text = " ".join(w["text"] for w in line).strip()
                            if text:
                                x0 = min(w["x0"] for w in line)
                                y0 = min(w["top"] for w in line)
                                x1 = max(w["x1"] for w in line)
                                y1 = max(w["bottom"] for w in line)
                                
                                # Detect font properties
                                font_size = line[0].get("size", 0) if line else 0
                                is_bold = any("Bold" in str(w.get("fontname", "")) 
                                            for w in line)
                                
                                block = TextBlock(
                                    text=text,
                                    x0=x0, y0=y0, x1=x1, y1=y1,
                                    page=page_num,
                                    font_size=font_size,
                                    is_bold=is_bold
                                )
                                blocks.append(block)
        except Exception as e:
            logger.error(f"Error extracting blocks from {pdf_path}: {e}")
        
        return blocks
    
    def _group_words_into_lines(self, words: List[Dict], 
                                 y_tolerance: float = 5) -> List[List[Dict]]:
        """Group words into lines based on vertical position."""
        if not words:
            return []
        
        # Sort by vertical position
        sorted_words = sorted(words, key=lambda w: (w["top"], w["x0"]))
        lines = []
        current_line = [sorted_words[0]]
        current_y = sorted_words[0]["top"]
        
        for word in sorted_words[1:]:
            if abs(word["top"] - current_y) <= y_tolerance:
                current_line.append(word)
            else:
                lines.append(sorted(current_line, key=lambda w: w["x0"]))
                current_line = [word]
                current_y = word["top"]
        
        if current_line:
            lines.append(sorted(current_line, key=lambda w: w["x0"]))
        
        return lines
    
    def classify_blocks(self, blocks: List[TextBlock]) -> List[TextBlock]:
        """Classify blocks as labels, values, or headers."""
        for block in blocks:
            text_lower = block.text.lower().strip()
            
            # Check if it looks like a label (ends with colon or separator)
            if re.search(r'[:\-–—]\s*$', block.text):
                block.block_type = "label"
                block.text = re.sub(r'[:\-–—]\s*$', '', block.text).strip()
            # Check if it matches known label patterns
            elif any(re.search(pattern, text_lower) 
                    for patterns in self.LABEL_PATTERNS.values() 
                    for pattern in patterns):
                block.block_type = "label"
            # Headers are typically bold, larger, or all caps
            elif block.is_bold or block.font_size > 12 or block.text.isupper():
                if len(block.text) < 100:
                    block.block_type = "header"
            else:
                block.block_type = "value_candidate"
        
        return blocks
    
    def find_label_value_pairs(self, blocks: List[TextBlock], 
                                max_distance: float = 150) -> List[FieldPattern]:
        """Find label-value pairs using spatial proximity."""
        pairs = []
        labels = [b for b in blocks if b.block_type == "label"]
        values = [b for b in blocks if b.block_type == "value_candidate"]
        
        for label in labels:
            # Find closest value candidates
            candidates = []
            for value in values:
                dist = label.distance_to(value)
                if dist < max_distance:
                    # Determine direction (right or below)
                    is_right = value.x0 > label.x1
                    is_below = value.y0 > label.y1
                    
                    if is_right or is_below:
                        candidates.append((value, dist, is_right, is_below))
            
            if candidates:
                # Prioritize: right first, then below
                candidates.sort(key=lambda x: (not x[2], x[1]))
                best_match = candidates[0][0]
                pairs.append(FieldPattern(label=label, value=best_match))
            else:
                pairs.append(FieldPattern(label=label, value=None))
        
        return pairs
    
    def semantic_classify_fields(self, pairs: List[FieldPattern], 
                                  api_key: Optional[str] = None) -> List[FieldPattern]:
        """Use LLM to classify field types semantically."""
        if not api_key or not OPENAI_AVAILABLE:
            # Fallback to pattern matching
            return self._classify_with_patterns(pairs)
        
        try:
            client = OpenAI(api_key=api_key)
            
            # Prepare field data for classification
            fields_data = []
            for i, pair in enumerate(pairs):
                fields_data.append({
                    "index": i,
                    "label": pair.label.text,
                    "value": pair.value.text if pair.value else None
                })
            
            prompt = f"""Classify these form fields into standard types.
Available types: name, id_number, phone, address, dob, email, unknown

Fields:
{json.dumps(fields_data, indent=2)}

Return JSON array with objects containing "index" and "field_type".
Be flexible with label variations - "Customer Name" = name, "ID #" = id_number, etc."""
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You classify form fields. Output only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
            )
            
            content = response.choices[0].message.content
            content = re.sub(r"^```\w*\n?", "", content)
            content = re.sub(r"\n?```$", "", content)
            classifications = json.loads(content.strip())
            
            # Apply classifications
            for cls in classifications:
                idx = cls.get("index", -1)
                if 0 <= idx < len(pairs):
                    pairs[idx].field_type = cls.get("field_type", "unknown")
                    pairs[idx].confidence = 0.9
            
        except Exception as e:
            logger.warning(f"LLM classification failed: {e}")
            return self._classify_with_patterns(pairs)
        
        return pairs
    
    def _classify_with_patterns(self, pairs: List[FieldPattern]) -> List[FieldPattern]:
        """Classify fields using regex patterns."""
        for pair in pairs:
            label_text = pair.label.text.lower()
            
            for field_type, patterns in self.LABEL_PATTERNS.items():
                if any(re.search(p, label_text) for p in patterns):
                    pair.field_type = field_type
                    pair.confidence = 0.7
                    break
            else:
                pair.field_type = "unknown"
                pair.confidence = 0.3
        
        return pairs
    
    def learn_template(self, pdf_paths: List[Path], 
                       api_key: Optional[str] = None) -> Template:
        """Learn template from multiple PDF samples."""
        all_patterns = defaultdict(list)
        
        for pdf_path in pdf_paths[:5]:  # Use first 5 PDFs to learn
            blocks = self.extract_blocks(pdf_path)
            blocks = self.classify_blocks(blocks)
            pairs = self.find_label_value_pairs(blocks)
            pairs = self.semantic_classify_fields(pairs, api_key)
            
            for pair in pairs:
                if pair.field_type != "unknown":
                    all_patterns[pair.field_type].append({
                        "label_text": pair.label.text,
                        "x": pair.label.x0,
                        "y": pair.label.y0,
                        "page": pair.label.page
                    })
        
        # Create template
        template_id = hashlib.md5(
            str(sorted(all_patterns.keys())).encode()
        ).hexdigest()[:12]
        
        template = Template(template_id=template_id)
        
        # Average positions for each field type
        for field_type, positions in all_patterns.items():
            if positions:
                avg_x = sum(p["x"] for p in positions) / len(positions)
                avg_y = sum(p["y"] for p in positions) / len(positions)
                template.field_positions[field_type] = {
                    "avg_x": avg_x,
                    "avg_y": avg_y,
                    "label_variations": list(set(p["label_text"] for p in positions)),
                    "count": len(positions)
                }
        
        template.sample_count = len(pdf_paths[:5])
        self.templates[template_id] = template
        self.current_template = template
        
        logger.info(f"Learned template {template_id} with {len(template.field_positions)} fields")
        return template
    
    def extract_with_template(self, pdf_path: Path, 
                              template: Template,
                              api_key: Optional[str] = None) -> Dict[str, Any]:
        """Extract data using learned template."""
        blocks = self.extract_blocks(pdf_path)
        blocks = self.classify_blocks(blocks)
        
        result = {}
        confidence_scores = {}
        
        for field_type, position_info in template.field_positions.items():
            avg_x = position_info["avg_x"]
            avg_y = position_info["avg_y"]
            
            # Find closest block to expected position
            best_match = None
            best_distance = float('inf')
            
            for block in blocks:
                if block.block_type in ["value_candidate", "unknown"]:
                    dist = ((block.center_x - avg_x) ** 2 + 
                           (block.center_y - avg_y) ** 2) ** 0.5
                    if dist < best_distance and dist < 200:  # Within 200 pixels
                        best_distance = dist
                        best_match = block
            
            if best_match:
                result[field_type] = best_match.text
                confidence_scores[field_type] = max(0.5, 1.0 - (best_distance / 200))
            else:
                result[field_type] = None
                confidence_scores[field_type] = 0.0
        
        # Also run semantic classification for any missed fields
        pairs = self.find_label_value_pairs(blocks)
        pairs = self.semantic_classify_fields(pairs, api_key)
        
        for pair in pairs:
            if pair.field_type != "unknown" and pair.value:
                if pair.field_type not in result or not result[pair.field_type]:
                    result[pair.field_type] = pair.value.text
                    confidence_scores[pair.field_type] = pair.confidence
        
        return {
            "fields": result,
            "confidence_scores": confidence_scores,
            "template_id": template.template_id
        }


# Global analyzer instance
layout_analyzer = LayoutAnalyzer()


def extract_structured_data(pdf_path: Path, 
                            template: Optional[Template] = None,
                            api_key: Optional[str] = None) -> Dict[str, Any]:
    """Main extraction function - layout aware and template-based."""
    analyzer = LayoutAnalyzer()
    
    if template:
        # Use existing template
        return analyzer.extract_with_template(pdf_path, template, api_key)
    else:
        # One-time extraction without template learning
        blocks = analyzer.extract_blocks(pdf_path)
        blocks = analyzer.classify_blocks(blocks)
        pairs = analyzer.find_label_value_pairs(blocks)
        pairs = analyzer.semantic_classify_fields(pairs, api_key)
        
        result = {}
        confidence_scores = {}
        
        for pair in pairs:
            if pair.value and pair.field_type != "unknown":
                result[pair.field_type] = pair.value.text
                confidence_scores[pair.field_type] = pair.confidence
        
        return {
            "fields": result,
            "confidence_scores": confidence_scores,
            "template_id": None,
            "raw_pairs": [p.to_dict() for p in pairs]
        }
