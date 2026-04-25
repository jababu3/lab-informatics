from fastapi import APIRouter, Depends, Query
from datetime import datetime

from models.schemas import Experiment
from api.database import MONGO_AVAILABLE, experiments_collection
from api.auth import get_current_user
from api.postgres import User

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.post("/")
async def create_experiment(
    exp: Experiment,
    current_user: User = Depends(get_current_user),
):
    data = exp.dict()
    data["created_at"] = datetime.now()
    if MONGO_AVAILABLE and experiments_collection is not None:
        result = experiments_collection.insert_one(data)
        data["_id"] = str(result.inserted_id)
    return {"status": "success", "experiment": data}


@router.get("/")
async def list_experiments(
    limit: int = Query(50, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
):
    if not MONGO_AVAILABLE or experiments_collection is None:
        return {"experiments": [], "total": 0}

    exps = list(experiments_collection.find().skip(skip).limit(limit))
    for e in exps:
        e["_id"] = str(e["_id"])

    return {"experiments": exps, "total": experiments_collection.count_documents({})}
