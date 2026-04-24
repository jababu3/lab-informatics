from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from services.provenance import save_raw_file
from api.database import MONGO_AVAILABLE
from api.auth import get_current_user
from api.postgres import User

# Use a mock collection if we don't want to rely on the current DB module layout, or just try to import:
try:
    from api.database import db
    raw_files_collection = db.raw_files if db is not None else None
except ImportError:
    raw_files_collection = None

router = APIRouter(prefix="/ingestion", tags=["ingestion"])

@router.post("/upload_raw")
async def upload_raw_data(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    try:
        # 1. Save locally and block modifications
        file_record = await save_raw_file(file)
        
        # 2. Record to database for future linking
        if MONGO_AVAILABLE and raw_files_collection is not None:
            result = raw_files_collection.insert_one(file_record.copy())
            file_record["_id"] = str(result.inserted_id)

        return {
            "status": "success",
            "message": "Raw file archived immutably.",
            "record": file_record
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
