"""Layout-aware extraction API endpoints."""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, WebSocket
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models_db import User, Job
from app.services.auth import get_current_user
from app.services.batch_processor import BatchProcessor, process_pdf_batch
from app.services.layout_extractor import LayoutAnalyzer, extract_structured_data, Template
from app.services.excel_generator import generate_excel
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/extraction", tags=["extraction"])
settings = get_settings()

# Store active processors (in production, use Redis or database)
active_processors: dict = {}


@router.post("/upload-batch")
async def upload_batch(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    learn_template: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a ZIP file containing PDFs for batch extraction.
    Automatically learns template from first few PDFs.
    """
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Only ZIP files are supported")
    
    try:
        content = await file.read()
        
        # Create job record
        job = Job(
            user_id=current_user.id,
            status="processing",
            total_files=0,
            processed_files=0
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        
        # Store processor for this job
        processor = BatchProcessor(max_workers=4)
        active_processors[job.id] = processor
        
        return {
            "job_id": job.id,
            "message": "Batch upload accepted. Use /batch-status/{job_id} to track progress.",
            "filename": file.filename
        }
        
    except Exception as e:
        logger.exception("Batch upload failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batch-status/{job_id}")
async def get_batch_status(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get status of a batch extraction job."""
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    processor = active_processors.get(job_id)
    template_info = processor.get_template_info() if processor else None
    
    return {
        "job_id": job.id,
        "status": job.status,
        "total_files": job.total_files,
        "processed_files": job.processed_files,
        "template_learned": template_info is not None,
        "template_info": template_info
    }


@router.post("/extract-single")
async def extract_single_pdf(
    file: UploadFile = File(...),
    use_template: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Extract data from a single PDF using layout-aware extraction.
    No hard-coded keywords - automatically detects fields.
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        import tempfile
        from pathlib import Path
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = Path(tmp.name)
        
        try:
            # Extract using layout-aware engine
            api_key = settings.openai_api_key or None
            result = extract_structured_data(tmp_path, None, api_key)
            
            return {
                "file_name": file.filename,
                "extraction": result,
                "fields_detected": list(result.get("fields", {}).keys()),
                "template_id": result.get("template_id")
            }
        finally:
            tmp_path.unlink(missing_ok=True)
            
    except Exception as e:
        logger.exception(f"Extraction failed for {file.filename}")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@router.post("/extract-zip-sync")
async def extract_zip_sync(
    file: UploadFile = File(...),
    learn_template: bool = True,
    current_user: User = Depends(get_current_user)
):
    """
    Synchronous batch extraction from ZIP file.
    Returns all results as JSON (use for small batches).
    """
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Only ZIP files are supported")
    
    try:
        content = await file.read()
        api_key = settings.openai_api_key or None
        
        results = await process_pdf_batch(content, api_key, max_workers=4)
        
        # Generate summary
        successful = sum(1 for r in results if not r.get("error"))
        fields_discovered = set()
        for r in results:
            fields_discovered.update(r.get("fields", {}).keys())
        
        return {
            "total_processed": len(results),
            "successful": successful,
            "failed": len(results) - successful,
            "fields_discovered": sorted(fields_discovered),
            "results": results
        }
        
    except Exception as e:
        logger.exception("Batch extraction failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export-excel")
async def export_excel(
    job_id: int,
    include_confidence: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export extraction results as Excel file.
    One row per PDF, columns for each detected field.
    """
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job not yet completed")
    
    try:
        # Get results from processor or database
        processor = active_processors.get(job_id)
        if not processor or not hasattr(processor, 'results'):
            raise HTTPException(status_code=404, detail="Results not available")
        
        excel_bytes = generate_excel(
            processor.results,
            include_confidence=include_confidence
        )
        
        return StreamingResponse(
            io.BytesIO(excel_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=extraction_results_{job_id}.xlsx"}
        )
        
    except Exception as e:
        logger.exception("Excel export failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/ws/batch-progress/{job_id}")
async def batch_progress_websocket(
    websocket: WebSocket,
    job_id: int
):
    """WebSocket for real-time batch progress updates."""
    await websocket.accept()
    
    try:
        processor = active_processors.get(job_id)
        if not processor:
            await websocket.send_json({"error": "Job not found"})
            await websocket.close()
            return
        
        # Send progress updates
        while True:
            summary = processor.get_summary()
            await websocket.send_json(summary)
            
            if summary.get("completed"):
                break
                
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.exception("WebSocket error")
        await websocket.send_json({"error": str(e)})
    finally:
        await websocket.close()


@router.post("/analyze-template")
async def analyze_template(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Analyze a sample PDF to detect template structure.
    Returns detected fields and their positions.
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        import tempfile
        from pathlib import Path
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = Path(tmp.name)
        
        try:
            analyzer = LayoutAnalyzer()
            blocks = analyzer.extract_blocks(tmp_path)
            blocks = analyzer.classify_blocks(blocks)
            pairs = analyzer.find_label_value_pairs(blocks)
            
            api_key = settings.openai_api_key or None
            pairs = analyzer.semantic_classify_fields(pairs, api_key)
            
            return {
                "file_name": file.filename,
                "total_blocks": len(blocks),
                "labels_detected": len([b for b in blocks if b.block_type == "label"]),
                "fields": [
                    {
                        "label": p.label.text,
                        "value": p.value.text if p.value else None,
                        "field_type": p.field_type,
                        "confidence": p.confidence,
                        "position": {
                            "x": p.label.x0,
                            "y": p.label.y0,
                            "page": p.label.page
                        }
                    }
                    for p in pairs
                ]
            }
        finally:
            tmp_path.unlink(missing_ok=True)
            
    except Exception as e:
        logger.exception("Template analysis failed")
        raise HTTPException(status_code=500, detail=str(e))
