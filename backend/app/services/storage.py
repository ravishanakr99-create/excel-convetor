"""Hybrid storage service - uses local or Supabase based on configuration."""
import logging
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from app.config import get_settings
from app.services.supabase_client import get_supabase_storage, get_supabase_db, is_supabase_enabled

logger = logging.getLogger(__name__)


class HybridStorage:
    """Storage service that switches between local and Supabase."""
    
    def __init__(self):
        self.settings = get_settings()
        self.use_supabase = is_supabase_enabled() and self.settings.storage_type == "supabase"
        logger.info(f"STORAGE_TYPE={self.settings.storage_type}, supabase_enabled={is_supabase_enabled()}")
        self.supabase_storage = get_supabase_storage()
        self.supabase_db = get_supabase_db()
        if self.use_supabase:
            logger.info("Using Supabase cloud storage")
        else:
            logger.info("Using local storage only")
    
    # ============ File Storage Operations ============
    
    def upload_pdf(self, job_id: str, file_name: str, file_data: bytes) -> Optional[str]:
        """Upload PDF file. Returns URL or path."""
        if self.use_supabase and self.supabase_storage:
            url = self.supabase_storage.upload_pdf(job_id, file_name, file_data)
            if url:
                logger.info(f"Uploaded to Supabase: {url}")
                return url
            logger.warning("Supabase upload failed, falling back to local")
        
        # Local storage
        upload_dir = self.settings.upload_path / job_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / file_name
        file_path.write_bytes(file_data)
        logger.info(f"Saved locally: {file_path}")
        return str(file_path)
    
    def upload_excel(self, job_id: str, file_data: bytes) -> Optional[str]:
        """Upload Excel file. Returns URL or path."""
        if self.use_supabase and self.supabase_storage:
            url = self.supabase_storage.upload_excel(job_id, file_data)
            if url:
                logger.info(f"Excel uploaded to Supabase: {url}")
                return url
            logger.warning("Supabase Excel upload failed, falling back to local")
        
        # Local storage
        output_path = self.settings.output_path / f"{job_id}.xlsx"
        output_path.write_bytes(file_data)
        logger.info(f"Excel saved locally: {output_path}")
        return str(output_path)
    
    def delete_job_files(self, job_id: str) -> bool:
        """Delete all files for a job."""
        success = True
        
        # Delete from Supabase if enabled
        if self.use_supabase and self.supabase_storage:
            success = self.supabase_storage.delete_job_files(job_id) and success
        
        # Delete local files
        try:
            upload_dir = self.settings.upload_path / job_id
            if upload_dir.exists():
                shutil.rmtree(upload_dir)
            
            output_file = self.settings.output_path / f"{job_id}.xlsx"
            if output_file.exists():
                output_file.unlink()
        except Exception as e:
            logger.error(f"Failed to delete local files: {e}")
            success = False
        
        return success
    
    def get_excel_path(self, job_id: str) -> Optional[Path]:
        """Get local Excel file path for download."""
        output_path = self.settings.output_path / f"{job_id}.xlsx"
        if output_path.exists():
            return output_path
        return None
    
    def download_pdf(self, job_id: str, file_name: str) -> Optional[bytes]:
        """Download PDF from cloud storage."""
        if self.use_supabase and self.supabase_storage:
            return self.supabase_storage.download_pdf(job_id, file_name)
        return None
    
    def download_excel(self, job_id: str) -> Optional[bytes]:
        """Download Excel from cloud storage."""
        if self.use_supabase and self.supabase_storage:
            return self.supabase_storage.download_pdf(job_id, "output.xlsx")
        return None


class HybridDatabase:
    """Database service that switches between local SQLite and Supabase."""
    
    def __init__(self):
        self.settings = get_settings()
        self.use_supabase = is_supabase_enabled() and self.settings.storage_type == "supabase"
        self.supabase_db = get_supabase_db()
    
    def create_job(self, job_data: Dict[str, Any]) -> bool:
        """Create a job record."""
        if self.use_supabase and self.supabase_db:
            result = self.supabase_db.create_job(job_data)
            if result:
                return True
            logger.warning("Supabase create failed, using local database")
        
        # Local database is handled by SQLAlchemy models
        return True  # Local DB handles this via the upload route
    
    def update_job(self, job_id: str, job_data: Dict[str, Any]) -> bool:
        """Update a job record."""
        if self.use_supabase and self.supabase_db:
            return self.supabase_db.update_job(job_id, job_data)
        return True  # Local DB handles this
    
    def get_user_jobs(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all jobs for a user."""
        if self.use_supabase and self.supabase_db:
            jobs = self.supabase_db.get_user_jobs(user_id, limit)
            if jobs:
                return jobs
        
        # Return empty - local DB will be queried by the route
        return []
    
    def delete_job(self, job_id: str, user_id: int) -> bool:
        """Delete a job."""
        if self.use_supabase and self.supabase_db:
            return self.supabase_db.delete_job(job_id, user_id)
        return True  # Local DB handles this


# Singleton instances
_hybrid_storage: Optional[HybridStorage] = None
_hybrid_db: Optional[HybridDatabase] = None


def get_hybrid_storage() -> HybridStorage:
    """Get hybrid storage instance."""
    global _hybrid_storage
    if _hybrid_storage is None:
        _hybrid_storage = HybridStorage()
    return _hybrid_storage


def get_hybrid_db() -> HybridDatabase:
    """Get hybrid database instance."""
    global _hybrid_db
    if _hybrid_db is None:
        _hybrid_db = HybridDatabase()
    return _hybrid_db
