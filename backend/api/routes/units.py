from fastapi import APIRouter, Depends, HTTPException
from services.unit_harmonization import standardize_concentration
from pydantic import BaseModel

from api.auth import get_current_user
from api.postgres import User

router = APIRouter(prefix="/units", tags=["unit-checker"])

class UnitConversionRequest(BaseModel):
    value: float
    unit: str
    target_unit: str = "uM"

@router.post("/harmonize/single")
async def harmonize_single(
    request: UnitConversionRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        # Standardize using the pint service
        result = standardize_concentration(request.value, request.unit, request.target_unit)
        return {
            "status": "success",
            "data": result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal unit conversion error.")
