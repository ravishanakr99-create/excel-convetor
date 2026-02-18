"""Upload and process API routes."""
import uuid
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.models_db import User, Job, JobStatusEnum
from app.services.auth import get_current_user
from app.config import get_settings
from app.services.excel_generator import generate_excel
from app.services.pdf_scanner import (
    scan_pdf, 
    scan_multiple_pdfs, 
    create_excel_from_scans,
    scan_zip_and_create_excel
)

router = APIRouter(prefix="/jobs", tags=["jobs"])
settings = get_settings()
logger = logging.getLogger(__name__)


def run_extraction(job_id: str):
    """Background task: scan PDFs and create Excel - NO hard-coded formats."""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job or job.status != JobStatusEnum.UPLOADED:
            return
        job.status = JobStatusEnum.PROCESSING
        db.commit()
        
        upload_path = settings.upload_path / job_id
        if not upload_path.exists():
            job.status = JobStatusEnum.FAILED
            job.error_message = "Upload directory not found"
            db.commit()
            return
        
        pdf_files = list(upload_path.glob("*.pdf"))
        pdf_paths = [p for p in pdf_files if p.is_file()]
        total = len(pdf_paths)
        
        if total == 0:
            job.status = JobStatusEnum.FAILED
            job.error_message = "No PDF files found"
            db.commit()
            return

        logger.info(f"Scanning {total} PDFs for job {job_id}")
        
        # Scan all PDFs - NO hard-coded formats, just read what's there
        results = []
        for i, pdf_path in enumerate(pdf_paths):
            try:
                # Update progress
                job.processed_files = i + 1
                job.progress_percent = ((i + 1) / total) * 100.0
                job.updated_at = datetime.utcnow()
                db.commit()
                
                # Simple scan - extracts whatever is in the PDF
                result = scan_pdf(pdf_path)
                results.append(result)
                
                logger.info(f"Scanned {pdf_path.name}: {len(result['fields'])} fields found")
                
            except Exception as e:
                logger.error(f"Failed to scan {pdf_path}: {e}")
                results.append({
                    "file_name": pdf_path.name,
                    "fields": {},
                    "raw_text": "",
                    "total_lines": 0,
                    "error": str(e)
                })
        
        # Create Excel from scanned data
        excel_bytes = create_excel_from_scans(results)
        out_path = settings.output_path / f"{job_id}.xlsx"
        out_path.write_bytes(excel_bytes)
        
        logger.info(f"Excel created: {out_path}")
        
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.extraction_results = results
            job.status = JobStatusEnum.COMPLETED
            job.progress_percent = 100.0
            job.processed_files = total
            job.updated_at = datetime.utcnow()
            db.commit()
            
    except Exception as e:
        logger.exception("Scanning failed")
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = JobStatusEnum.FAILED
            job.error_message = str(e)
            db.commit()
    finally:
        db.close()


@router.post("/upload")
async def upload_pdfs(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload multiple PDFs and create a job."""
    if len(files) > settings.max_upload_files:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {settings.max_upload_files} files allowed"
        )
    job_id = str(uuid.uuid4())
    upload_dir = settings.upload_path / job_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_names = []
    for f in files:
        if not f.filename or not f.filename.lower().endswith(".pdf"):
            continue
        content = await f.read()
        safe_name = f.filename.replace("..", "").replace("/", "_")
        dest = upload_dir / safe_name
        dest.write_bytes(content)
        file_names.append(f.filename)
    if not file_names:
        raise HTTPException(status_code=400, detail="No valid PDF files uploaded")
    job = Job(
        id=job_id,
        user_id=user.id,
        status=JobStatusEnum.UPLOADED,
        total_files=len(file_names),
        file_names=file_names,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    background_tasks.add_task(run_extraction, job_id)
    return {
        "job_id": job_id,
        "status": "uploaded",
        "total_files": len(file_names),
        "message": "Upload complete. Processing started.",
    }


class ProcessRequest(BaseModel):
    job_id: str


@router.post("/process")
async def start_process(
    body: ProcessRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None,
):
    job_id = body.job_id
    """Manually trigger processing (if job was uploaded separately)."""
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status == JobStatusEnum.PROCESSING:
        return {"job_id": job_id, "status": "processing", "message": "Already processing"}
    if job.status == JobStatusEnum.COMPLETED:
        return {"job_id": job_id, "status": "completed", "message": "Already completed"}
    if job.status != JobStatusEnum.UPLOADED:
        raise HTTPException(status_code=400, detail=f"Cannot process job in status {job.status}")
    if background_tasks:
        background_tasks.add_task(run_extraction, job_id)
    return {"job_id": job_id, "status": "processing", "message": "Processing started"}


@router.get("/status/{job_id}")
def get_status(
    job_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get processing status for a job."""
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job.id,
        "status": job.status.value,
        "total_files": job.total_files,
        "processed_files": job.processed_files,
        "progress_percent": job.progress_percent,
        "error_message": job.error_message,
        "file_names": job.file_names or [],
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
    }


@router.get("/download/{job_id}")
def download_excel(
    job_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download Excel file for completed job."""
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatusEnum.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Job not completed. Current status: {job.status.value}"
        )
    out_path = settings.output_path / f"{job_id}.xlsx"
    if not out_path.exists():
        raise HTTPException(status_code=404, detail="Excel file not found")
    return FileResponse(
        out_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"extraction_{job_id}.xlsx",
    )


@router.get("/results/{job_id}")
def get_results(
    job_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get extraction results for preview."""
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job.id,
        "status": job.status.value,
        "extraction_results": job.extraction_results or [],
        "total_files": job.total_files,
    }


@router.get("/history")
def get_history(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50,
):
    """Get user's job history."""
    jobs = (
        db.query(Job)
        .filter(Job.user_id == user.id)
        .order_by(Job.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "job_id": j.id,
            "name": j.name,
            "status": j.status.value,
            "total_files": j.total_files,
            "processed_files": j.processed_files,
            "created_at": j.created_at.isoformat(),
        }
        for j in jobs
    ]
