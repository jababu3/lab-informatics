from fastapi import APIRouter, HTTPException, Depends

from models.schemas import QSARData, DoseResponseData
from api.database import MONGO_AVAILABLE, compounds_collection, experiments_collection
from api.auth import get_current_user
from api.postgres import User
from services.analytics import train_qsar, fit_dose_response

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.post("/qsar/train")
async def qsar_train(
    data: QSARData,
    model_type: str = "random_forest",
    current_user: User = Depends(get_current_user),
):
    try:
        result = train_qsar(data.compounds, model_type)
        return result
    except Exception as e:
        raise HTTPException(400, str(e))

@router.post("/dose-response/fit")
async def dose_response_fit_endpoint(
    data: DoseResponseData,
    current_user: User = Depends(get_current_user),
):
    try:
        result = fit_dose_response(data.concentrations, data.responses)
        return result
    except Exception as e:
        raise HTTPException(400, str(e))

@router.get("/summary")
async def summary(current_user: User = Depends(get_current_user)):
    if not MONGO_AVAILABLE or compounds_collection is None or experiments_collection is None:
        return {"error": "Database unavailable"}

    return {
        "compounds": {"total": compounds_collection.count_documents({})},
        "experiments": {"total": experiments_collection.count_documents({})}
    }
