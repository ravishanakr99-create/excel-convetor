"""Supabase client for cloud storage and database."""
import logging
import requests
from typing import Optional, Dict, Any, List
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

SUPABASE_AVAILABLE = True


def is_supabase_enabled() -> bool:
    """Check if Supabase is configured and available."""
    supabase_url = getattr(settings, 'supabase_url', '') or ''
    supabase_key = getattr(settings, 'supabase_key', '') or ''
    
    return bool(supabase_url and supabase_key)


class SupabaseStorage:
    """Supabase storage operations for PDFs and Excel files using requests."""
    
    def __init__(self):
        self.bucket_name = "uploads"
        self.supabase_url = getattr(settings, 'supabase_url', '')
        self.supabase_key = getattr(settings, 'supabase_key', '')
        self.storage_url = f"{self.supabase_url}/storage/v1"
        self.headers = {
            "Authorization": f"Bearer {self.supabase_key}",
            "apikey": self.supabase_key
        }
        logger.info(f"SupabaseStorage initialized with URL: {self.supabase_url}")
    
    def upload_pdf(self, job_id: str, file_name: str, file_data: bytes) -> Optional[str]:
        """Upload PDF to Supabase Storage. Returns public URL."""
        logger.info(f"Uploading {file_name} to Supabase...")
        try:
            path = f"{job_id}/{file_name}"
            upload_url = f"{self.storage_url}/object/{self.bucket_name}/{path}"
            
            headers = self.headers.copy()
            headers["Content-Type"] = "application/pdf"
            headers["x-upsert"] = "true"
            
            response = requests.post(upload_url, headers=headers, data=file_data)
            
            if response.status_code in [200, 201]:
                public_url = f"{self.supabase_url}/storage/v1/object/public/{self.bucket_name}/{path}"
                logger.info(f"PDF uploaded successfully: {public_url}")
                return public_url
            else:
                logger.error(f"Upload failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Failed to upload PDF to Supabase: {e}")
            return None
    
    def upload_excel(self, job_id: str, file_data: bytes) -> Optional[str]:
        """Upload Excel to Supabase Storage. Returns public URL."""
        try:
            path = f"{job_id}/output.xlsx"
            upload_url = f"{self.storage_url}/object/{self.bucket_name}/{path}"
            
            headers = self.headers.copy()
            headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            headers["x-upsert"] = "true"
            
            response = requests.post(upload_url, headers=headers, data=file_data)
            
            if response.status_code in [200, 201]:
                public_url = f"{self.supabase_url}/storage/v1/object/public/{self.bucket_name}/{path}"
                logger.info(f"Excel uploaded successfully: {public_url}")
                return public_url
            else:
                logger.error(f"Excel upload failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Failed to upload Excel to Supabase: {e}")
            return None
    
    def download_pdf(self, job_id: str, file_name: str) -> Optional[bytes]:
        """Download PDF from Supabase Storage."""
        try:
            path = f"{job_id}/{file_name}"
            download_url = f"{self.storage_url}/object/{self.bucket_name}/{path}"
            
            response = requests.get(download_url, headers=self.headers)
            
            if response.status_code == 200:
                logger.info(f"Downloaded {file_name} from Supabase")
                return response.content
            else:
                logger.error(f"Download failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Failed to download PDF from Supabase: {e}")
            return None
    
    def delete_job_files(self, job_id: str) -> bool:
        """Delete all files for a job."""
        try:
            # List files first
            list_url = f"{self.storage_url}/object/list/{self.bucket_name}"
            response = requests.post(list_url, headers=self.headers, json={"prefix": f"{job_id}/"})
            
            if response.status_code == 200:
                files = response.json()
                for file in files:
                    delete_url = f"{self.storage_url}/object/{self.bucket_name}/{job_id}/{file['name']}"
                    requests.delete(delete_url, headers=self.headers)
                logger.info(f"Deleted files from Supabase for job {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete files from Supabase: {e}")
            return False


class SupabaseDatabase:
    """Supabase database operations for jobs and users - disabled for now."""
    
    def __init__(self):
        self.client = None  # Database operations disabled, using local SQLite
    
    def create_job(self, job_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return None
    
    def update_job(self, job_id: str, job_data: Dict[str, Any]) -> bool:
        return False
    
    def get_job(self, job_id: str, user_id: int) -> Optional[Dict[str, Any]]:
        return None
    
    def get_user_jobs(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        return []
    
    def delete_job(self, job_id: str, user_id: int) -> bool:
        return False


# Singleton instances
_supabase_storage: Optional[SupabaseStorage] = None
_supabase_db: Optional[SupabaseDatabase] = None


def get_supabase_storage() -> Optional[SupabaseStorage]:
    """Get Supabase storage instance."""
    global _supabase_storage
    if _supabase_storage is None and is_supabase_enabled():
        _supabase_storage = SupabaseStorage()
    return _supabase_storage


def get_supabase_db() -> Optional[SupabaseDatabase]:
    """Get Supabase database instance."""
    global _supabase_db
    if _supabase_db is None and is_supabase_enabled():
        _supabase_db = SupabaseDatabase()
    return _supabase_db
