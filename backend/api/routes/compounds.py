from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime

from models.schemas import Compound
from api.database import MONGO_AVAILABLE, compounds_collection
from api.auth import get_current_user
from api.postgres import User
from services.chemistry import calculate_descriptors, generate_svg, check_lipinski, RDKIT_AVAILABLE

try:
    from bson import ObjectId
    from bson.errors import InvalidId
except ImportError:
    pass

try:
    from rdkit import Chem
    from rdkit.Chem import AllChem
    from rdkit import DataStructs
except ImportError:
    pass

router = APIRouter(prefix="/compounds", tags=["compounds"])

@router.post("/")
async def create_compound(
    compound: Compound,
    current_user: User = Depends(get_current_user),
):
    desc = calculate_descriptors(compound.smiles)
    data = compound.dict()
    data.update(desc)
    data["svg_structure"] = generate_svg(compound.smiles)
    data["lipinski"] = check_lipinski(data)
    data["created_at"] = datetime.now()

    if MONGO_AVAILABLE and compounds_collection is not None:
        result = compounds_collection.insert_one(data)
        data["_id"] = str(result.inserted_id)

    return {"status": "success", "compound": data}

@router.get("/")
async def list_compounds(
    limit: int = Query(50, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
):
    if not MONGO_AVAILABLE or compounds_collection is None:
        return {"compounds": [], "total": 0}

    compounds = list(compounds_collection.find().skip(skip).limit(limit))
    for c in compounds:
        c["_id"] = str(c["_id"])

    return {"compounds": compounds, "total": compounds_collection.count_documents({})}

@router.get("/{compound_id}")
async def get_compound(
    compound_id: str,
    current_user: User = Depends(get_current_user),
):
    if not MONGO_AVAILABLE or compounds_collection is None:
        raise HTTPException(503, "Database unavailable")

    try:
        oid = ObjectId(compound_id)
    except InvalidId:
        raise HTTPException(400, "Invalid ID format")

    compound = compounds_collection.find_one({"_id": oid})
    if not compound:
        raise HTTPException(404, "Not found")
    compound["_id"] = str(compound["_id"])
    return compound

@router.post("/similarity/search")
async def similarity_search(
    smiles: str,
    threshold: float = 0.7,
    current_user: User = Depends(get_current_user),
):
    if not RDKIT_AVAILABLE or not MONGO_AVAILABLE or compounds_collection is None:
        raise HTTPException(503, "Services unavailable")

    try:
        target_mol = Chem.MolFromSmiles(smiles)
        if not target_mol:
            raise HTTPException(400, "Invalid SMILES")

        target_fp = AllChem.GetMorganFingerprint(target_mol, 2)
        similar = []

        for comp in compounds_collection.find():
            mol = Chem.MolFromSmiles(comp["smiles"])
            if mol:
                fp = AllChem.GetMorganFingerprint(mol, 2)
                sim = DataStructs.TanimotoSimilarity(target_fp, fp)
                if sim >= threshold:
                    comp["_id"] = str(comp["_id"])
                    comp["similarity"] = float(sim)
                    similar.append(comp)

        similar.sort(key=lambda x: x["similarity"], reverse=True)
        return {"results": similar[:20]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
