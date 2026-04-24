import os
import hashlib
import shutil
from fastapi import UploadFile

RAW_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "raw_data_archive")

def ensure_archive_exists():
    if not os.path.exists(RAW_DATA_DIR):
        os.makedirs(RAW_DATA_DIR)

def calculate_sha256(file_path: str) -> str:
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

async def save_raw_file(upload_file: UploadFile) -> dict:
    ensure_archive_exists()
    
    # We use the original filename, but in production this might need a UUID to prevent collisions
    safe_filename = upload_file.filename.replace(" ", "_")
    destination_path = os.path.join(RAW_DATA_DIR, safe_filename)
    
    with open(destination_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
        
    file_hash = calculate_sha256(destination_path)
    
    return {
        "filename": safe_filename,
        "sha256_hash": file_hash,
        "storage_path": destination_path
    }
