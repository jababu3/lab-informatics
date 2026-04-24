from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class RawFileRecord(BaseModel):
    filename: str
    sha256_hash: str
    upload_timestamp: datetime = Field(default_factory=datetime.now)
    storage_path: str

class HarmonizedMeasurement(BaseModel):
    original_value: float
    original_unit: str
    harmonized_value: float
    harmonized_unit: str = "uM"
    source_file_id: Optional[str] = None
