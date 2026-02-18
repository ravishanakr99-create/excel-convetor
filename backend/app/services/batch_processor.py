"""Batch processing service for handling large PDF collections."""
import asyncio
import io
import logging
import zipfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, AsyncGenerator
from concurrent.futures import ThreadPoolExecutor
import tempfile
import shutil

from app.services.layout_extractor import (
    LayoutAnalyzer, extract_structured_data, Template
)
from app.services.pdf_processor import detect_if_scanned, pdf_to_images, ocr_images
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class BatchProcessor:
    """Handles batch processing of PDFs with async operations."""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.analyzer = LayoutAnalyzer()
        self.template: Optional[Template] = None
        self.processed_count = 0
        self.failed_files: List[str] = []
    
    async def process_zip_upload(
        self,
        zip_content: bytes,
        api_key: Optional[str] = None,
        learn_template: bool = True,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process a ZIP file containing PDFs.
        Yields results as they complete.
        """
        # Extract ZIP to temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            pdf_files = await self._extract_zip(zip_content, temp_path)
            
            if not pdf_files:
                yield {"error": "No PDF files found in ZIP"}
                return
            
            total = len(pdf_files)
            
            # Learn template from first few PDFs if requested
            if learn_template and len(pdf_files) >= 2:
                if progress_callback:
                    progress_callback(0, total, "Learning template from samples...")
                
                self.template = await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    self.analyzer.learn_template,
                    pdf_files[:5],
                    api_key
                )
            
            # Process all PDFs
            processed = 0
            for pdf_file in pdf_files:
                processed += 1
                
                if progress_callback:
                    progress_callback(processed, total, pdf_file.name)
                
                try:
                    result = await self._process_single_pdf(
                        pdf_file, api_key
                    )
                    result["sequence"] = processed
                    result["total"] = total
                    yield result
                    
                except Exception as e:
                    logger.error(f"Failed to process {pdf_file}: {e}")
                    self.failed_files.append(pdf_file.name)
                    yield {
                        "file_name": pdf_file.name,
                        "error": str(e),
                        "sequence": processed,
                        "total": total,
                        "fields": {},
                        "confidence_scores": {}
                    }
    
    async def _extract_zip(self, zip_content: bytes, 
                          extract_dir: Path) -> List[Path]:
        """Extract ZIP and return list of PDF files."""
        pdf_files = []
        
        try:
            with zipfile.ZipFile(io.BytesIO(zip_content), 'r') as zf:
                for member in zf.namelist():
                    # Skip directories and hidden files
                    if member.endswith('/') or member.startswith('__'):
                        continue
                    
                    # Check if it's a PDF
                    if member.lower().endswith('.pdf'):
                        # Extract
                        zf.extract(member, extract_dir)
                        extracted_path = extract_dir / member
                        
                        # Handle nested paths - flatten structure
                        if '/' in member or '\\' in member:
                            flat_name = member.replace('/', '_').replace('\\', '_')
                            flat_path = extract_dir / flat_name
                            shutil.move(str(extracted_path), str(flat_path))
                            pdf_files.append(flat_path)
                        else:
                            pdf_files.append(extracted_path)
        
        except zipfile.BadZipFile:
            logger.error("Invalid ZIP file")
        except Exception as e:
            logger.error(f"Error extracting ZIP: {e}")
        
        return sorted(pdf_files)
    
    async def _process_single_pdf(
        self,
        pdf_path: Path,
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a single PDF with error handling."""
        
        def _process():
            try:
                # Check if scanned
                is_scanned = detect_if_scanned(pdf_path)
                
                # Extract with layout analyzer
                if self.template:
                    result = self.analyzer.extract_with_template(
                        pdf_path, self.template, api_key
                    )
                else:
                    result = extract_structured_data(pdf_path, None, api_key)
                
                # Add metadata
                result["file_name"] = pdf_path.name
                result["file_path"] = str(pdf_path)
                result["is_scanned"] = is_scanned
                result["error"] = None
                
                return result
                
            except Exception as e:
                logger.exception(f"Error processing {pdf_path}")
                return {
                    "file_name": pdf_path.name,
                    "file_path": str(pdf_path),
                    "fields": {},
                    "confidence_scores": {},
                    "is_scanned": False,
                    "error": str(e)
                }
        
        # Run in thread pool
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, _process
        )
    
    def get_template_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the learned template."""
        if not self.template:
            return None
        
        return {
            "template_id": self.template.template_id,
            "field_count": len(self.template.field_positions),
            "fields": list(self.template.field_positions.keys()),
            "sample_count": self.template.sample_count,
            "field_positions": self.template.field_positions
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get processing summary."""
        return {
            "processed": self.processed_count,
            "failed": len(self.failed_files),
            "failed_files": self.failed_files,
            "template_learned": self.template is not None
        }


async def process_pdf_batch(
    zip_content: bytes,
    api_key: Optional[str] = None,
    max_workers: int = 4
) -> List[Dict[str, Any]]:
    """
    Convenience function to process a batch of PDFs.
    Returns all results as a list.
    """
    processor = BatchProcessor(max_workers=max_workers)
    results = []
    
    async for result in processor.process_zip_upload(
        zip_content, api_key, learn_template=True
    ):
        results.append(result)
    
    return results
