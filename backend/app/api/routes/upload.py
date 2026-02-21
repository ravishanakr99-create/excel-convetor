"""Upload and process API routes."""
import uuid
import asyncio
import logging
import tempfile
import shutil
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
from app.services.extraction_engine import process_single_pdf, process_batch
from app.services.storage import get_hybrid_storage

router = APIRouter(prefix="/jobs", tags=["jobs"])
settings = get_settings()
logger = logging.getLogger(__name__)
storage = get_hybrid_storage()


def run_extraction_with_cloud_upload(job_id: str):
    """Background task: process PDFs locally (fast), then upload to cloud."""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job or job.status != JobStatusEnum.UPLOADED:
            return
        job.status = JobStatusEnum.PROCESSING
        db.commit()
        
        # Get list of uploaded files from database
        file_names = job.file_names or []
        total = len(file_names)
        
        if total == 0:
            job.status = JobStatusEnum.FAILED
            job.error_message = "No PDF files found"
            db.commit()
            return

        logger.info(f"Processing {total} PDFs for job {job_id}")
        
        # Use local files directly (fast)
        upload_path = settings.upload_path / job_id
        pdf_paths = []
        for file_name in file_names:
            safe_name = file_name.replace("..", "").replace("/", "_")
            local_path = upload_path / safe_name
            if local_path.exists():
                pdf_paths.append(local_path)
            else:
                logger.warning(f"File not found: {safe_name}")
        
        if not pdf_paths:
            job.status = JobStatusEnum.FAILED
            job.error_message = "Could not retrieve PDF files"
            db.commit()
            return
        
        # Process all PDFs (fast - local files)
        results = []
        for i, pdf_path in enumerate(pdf_paths):
            try:
                result = process_single_pdf(pdf_path)
                results.append(result)
                
                # Update progress
                job.processed_files = i + 1
                job.progress_percent = ((i + 1) / total) * 100.0
                job.updated_at = datetime.utcnow()
                db.commit()
                
                logger.info(f"Processed {pdf_path.name}: {len(result.get('fields', {}))} fields found")
            except Exception as e:
                logger.error(f"Failed to process {pdf_path}: {e}")
                results.append({
                    "file_name": pdf_path.name,
                    "fields": {}
                })
        
        # Create Excel
        excel_bytes = generate_excel(results)
        
        # Save locally first (fast) - keep local for fast downloads
        out_path = settings.output_path / f"{job_id}.xlsx"
        out_path.write_bytes(excel_bytes)
        logger.info(f"Excel saved locally: {out_path}")
        
        # Mark job as ready for download - files stay local for fast download
        logger.info(f"Job {job_id} ready for fast local download")
        
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
    """Upload multiple PDFs - save locally first for fast processing, then upload to cloud."""
    if len(files) > settings.max_upload_files:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {settings.max_upload_files} files allowed"
        )
    job_id = str(uuid.uuid4())
    upload_dir = settings.upload_path / job_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_names = []
    
    # Save files locally first (fast)
    for f in files:
        if not f.filename or not f.filename.lower().endswith(".pdf"):
            continue
        content = await f.read()
        safe_name = f.filename.replace("..", "").replace("/", "_")
        
        # Save locally first (fast)
        local_path = upload_dir / safe_name
        local_path.write_bytes(content)
        file_names.append(f.filename)
        logger.info(f"Saved {safe_name} locally")
    
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
    
    # Process locally first, then upload to cloud in background
    background_tasks.add_task(run_extraction_with_cloud_upload, job_id)
    
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
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download Excel file - fast local download, then upload to cloud and cleanup."""
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatusEnum.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Job not completed. Current status: {job.status.value}"
        )
    
    out_path = settings.output_path / f"{job_id}.xlsx"
    upload_path = settings.upload_path / job_id
    
    # If local file exists, serve it fast
    if out_path.exists():
        # Schedule cloud upload and cleanup after download
        background_tasks.add_task(upload_to_cloud_and_cleanup, job_id, upload_path, out_path)
        
        return FileResponse(
            out_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=f"extraction_{job_id}.xlsx",
        )
    
    # If not local, try to download from Supabase
    try:
        excel_data = storage.download_excel(job_id)
        if excel_data:
            out_path.write_bytes(excel_data)
            return FileResponse(
                out_path,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                filename=f"extraction_{job_id}.xlsx",
            )
    except Exception as e:
        logger.error(f"Failed to download from Supabase: {e}")
    
    raise HTTPException(status_code=404, detail="Excel file not found")


def upload_to_cloud_and_cleanup(job_id: str, upload_path: Path, out_path: Path):
    """Upload files to Supabase after download, then cleanup local files."""
    try:
        logger.info(f"Starting cloud upload for job {job_id}")
        
        # Upload PDFs to cloud
        if upload_path.exists():
            for pdf_file in upload_path.glob("*.pdf"):
                file_data = pdf_file.read_bytes()
                storage.upload_pdf(job_id, pdf_file.name, file_data)
                pdf_file.unlink()
                logger.info(f"Uploaded and deleted PDF: {pdf_file.name}")
            
            # Remove empty upload directory
            if not any(upload_path.iterdir()):
                upload_path.rmdir()
        
        # Upload Excel to cloud
        if out_path.exists():
            excel_data = out_path.read_bytes()
            storage.upload_excel(job_id, excel_data)
            out_path.unlink()
            logger.info(f"Uploaded and deleted Excel for job {job_id}")
        
        logger.info(f"All files moved to cloud for job {job_id}")
    except Exception as e:
        logger.error(f"Cloud upload failed: {e}")


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


@router.delete("/delete/{job_id}")
def delete_job(
    job_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a job and its associated files from cloud and local storage."""
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Delete from cloud storage (Supabase)
    storage.delete_job_files(job_id)
    
    # Delete local uploaded files
    upload_dir = settings.upload_path / job_id
    if upload_dir.exists():
        import shutil
        shutil.rmtree(upload_dir)
    
    # Delete local output Excel file
    out_path = settings.output_path / f"{job_id}.xlsx"
    if out_path.exists():
        out_path.unlink()
    
    # Delete from database
    db.delete(job)
    db.commit()
    
    return {"message": "Job deleted successfully", "job_id": job_id}


@router.delete("/delete-all")
def delete_all_jobs(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete all jobs and their associated files for the current user."""
    jobs = db.query(Job).filter(Job.user_id == user.id).all()
    
    deleted_count = 0
    for job in jobs:
        # Delete from cloud storage (Supabase)
        storage.delete_job_files(job.id)
        
        # Delete local uploaded files
        upload_dir = settings.upload_path / job.id
        if upload_dir.exists():
            import shutil
            shutil.rmtree(upload_dir)
        
        # Delete local output Excel file
        out_path = settings.output_path / f"{job.id}.xlsx"
        if out_path.exists():
            out_path.unlink()
        
        # Delete from database
        db.delete(job)
        deleted_count += 1
    
    db.commit()
    
    return {"message": f"All jobs deleted successfully", "deleted_count": deleted_count}


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
