from typing import Dict

try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, AllChem, Draw  # noqa: F401
    from rdkit.Chem.Draw import rdMolDraw2D
    from rdkit import DataStructs  # noqa: F401

    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False


def calculate_descriptors(smiles: str) -> Dict:
    if not RDKIT_AVAILABLE:
        return {}
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return {}
        return {
            "molecular_weight": Descriptors.MolWt(mol),
            "logp": Descriptors.MolLogP(mol),
            "tpsa": Descriptors.TPSA(mol),
            "hbd": Descriptors.NumHDonors(mol),
            "hba": Descriptors.NumHAcceptors(mol),
            "rotatable_bonds": Descriptors.NumRotatableBonds(mol),
        }
    except Exception:
        return {}


def generate_svg(smiles: str) -> str:
    if not RDKIT_AVAILABLE:
        return ""
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol:
            drawer = rdMolDraw2D.MolDraw2DSVG(300, 300)
            drawer.DrawMolecule(mol)
            drawer.FinishDrawing()
            return drawer.GetDrawingText()
    except Exception:
        pass
    return ""


def check_lipinski(comp: dict) -> dict:
    violations = []
    if comp.get("molecular_weight", 0) > 500:
        violations.append("MW")
    if comp.get("logp", 0) > 5:
        violations.append("LogP")
    if comp.get("hbd", 0) > 5:
        violations.append("HBD")
    if comp.get("hba", 0) > 10:
        violations.append("HBA")
    return {"compliant": len(violations) <= 1, "violations": violations}
