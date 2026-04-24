#!/bin/bash
# Lab Informatics - Complete Automated Project Generator
# Everything included - just run this script!
# Usage: bash generate_project.sh

set -e

PROJECT_NAME="lab-informatics"
echo "🧪 Generating Complete Lab Informatics Project..."
echo "=================================================="

# Create directory structure
echo "📁 Creating directory structure..."
mkdir -p $PROJECT_NAME/{backend,frontend/src/{pages,components},scripts,docs/examples}
cd $PROJECT_NAME

# ============================================================================
# CONFIGURATION FILES
# ============================================================================

echo "📝 Creating configuration files..."

cat > .gitignore << 'EOF'
__pycache__/
*.py[cod]
.Python
venv/
node_modules/
.next/
.env
.env.local
.vscode/
.idea/
.DS_Store
*.log
mongo-data/
postgres-data/
EOF

cat > .env.example << 'EOF'
MONGO_USERNAME=labuser
MONGO_PASSWORD=changeme
POSTGRES_PASSWORD=changeme
DEBUG=true
EOF

cat > Makefile << 'EOF'
.PHONY: help setup start stop logs seed clean

help:
	@echo "Lab Informatics Commands:"
	@echo "  make setup   - Initial setup"
	@echo "  make start   - Start all services"
	@echo "  make stop    - Stop services"
	@echo "  make logs    - View logs"
	@echo "  make seed    - Load sample data"
	@echo "  make clean   - Remove everything"

setup:
	@cp .env.example .env
	@chmod +x scripts/*.sh scripts/*.py
	@echo "✅ Setup complete!"
	@echo "Edit .env then run: make start"

start:
	docker-compose up -d
	@echo "✅ Started!"
	@echo "Frontend: http://localhost:3000"
	@echo "API: http://localhost:8000/docs"

stop:
	docker-compose down

logs:
	docker-compose logs -f

seed:
	@sleep 5
	docker-compose exec backend python /app/scripts/seed_data.py

clean:
	docker-compose down -v
EOF

cat > README.md << 'EOF'
# Lab Informatics

Python-based electronic lab notebook for small molecule drug discovery.

## Quick Start

```bash
make setup
# Edit .env with passwords
make start
make seed
```

**Access:**
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs

## Features

- 🧪 Compound management (RDKit)
- 📊 QSAR modeling (scikit-learn)
- 📈 Dose-response curves (scipy)
- 🔍 Similarity search
- 📱 React dashboard

## Stack

- Python (FastAPI + RDKit + scikit-learn + scipy)
- React/Next.js
- MongoDB + PostgreSQL/ChEMBL
- Docker

## Commands

- `make start` - Start services
- `make stop` - Stop services
- `make logs` - View logs
- `make seed` - Load sample data
- `make clean` - Reset everything

## License

MIT
EOF

cat > LICENSE << 'EOF'
MIT License

Copyright (c) 2025 Lab Informatics Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
EOF

cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  mongodb:
    image: mongo:7.0
    container_name: lab-mongodb
    restart: always
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_ROOT_USERNAME: ${MONGO_USERNAME:-labuser}
      MONGO_INITDB_ROOT_PASSWORD: ${MONGO_PASSWORD:-labpassword}
    volumes:
      - mongodb_data:/data/db
    networks:
      - lab-network

  # Simple PostgreSQL (ChEMBL optional - see docs/chembl-setup.md)
  postgres:
    image: postgres:15
    container_name: lab-postgres
    restart: always
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: labuser
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-labpassword}
      POSTGRES_DB: lab_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - lab-network

  backend:
    build: ./backend
    container_name: lab-backend
    restart: always
    ports:
      - "8000:8000"
    environment:
      - MONGODB_URL=mongodb://${MONGO_USERNAME:-labuser}:${MONGO_PASSWORD:-labpassword}@mongodb:27017/lab_informatics
      - POSTGRES_URL=postgresql://labuser:${POSTGRES_PASSWORD:-labpassword}@postgres:5432/lab_db
    volumes:
      - ./backend:/app
      - ./scripts:/app/scripts
    depends_on:
      - mongodb
      - postgres
    networks:
      - lab-network

  frontend:
    build: ./frontend
    container_name: lab-frontend
    restart: always
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    volumes:
      - ./frontend:/app
      - /app/node_modules
      - /app/.next
    depends_on:
      - backend
    networks:
      - lab-network

volumes:
  mongodb_data:
  postgres_data:

networks:
  lab-network:
    driver: bridge
EOF

# ============================================================================
# BACKEND - Complete Python Code
# ============================================================================

echo "🐍 Creating complete backend..."

cat > backend/Dockerfile << 'EOF'
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    libcairo2-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
EOF

cat > backend/requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
pymongo==4.6.0
psycopg2-binary==2.9.9
rdkit-pypi==2022.9.5
numpy==1.24.3
pandas==2.0.3
scipy==1.11.3
scikit-learn==1.3.2
python-multipart==0.0.6
python-dotenv==1.0.0
requests==2.31.0
EOF

# Complete backend main.py with all analytics
cat > backend/main.py << 'PYTHON_EOF'
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
import numpy as np
import pandas as pd

# RDKit
try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, AllChem, Draw
    from rdkit.Chem.Draw import rdMolDraw2D
    from rdkit import DataStructs
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False

# ML & Stats
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_squared_error
from scipy.optimize import curve_fit
from scipy import stats

# MongoDB
try:
    from pymongo import MongoClient
    mongo_client = MongoClient(os.getenv("MONGODB_URL", "mongodb://localhost:27017/"))
    db = mongo_client.lab_informatics
    compounds_collection = db.compounds
    experiments_collection = db.experiments
    MONGO_AVAILABLE = True
    print("✅ MongoDB connected")
except Exception as e:
    MONGO_AVAILABLE = False
    print(f"⚠️  MongoDB: {e}")

app = FastAPI(title="Lab Informatics API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class Compound(BaseModel):
    name: str
    smiles: str
    tags: List[str] = []

class Experiment(BaseModel):
    title: str
    description: str
    compound_ids: List[str]
    assay_type: str
    target: Optional[str] = None
    status: str = "planned"

class DoseResponseData(BaseModel):
    concentrations: List[float]
    responses: List[float]

class QSARData(BaseModel):
    compounds: List[Dict[str, Any]]

# Chemistry Functions
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
            "rotatable_bonds": Descriptors.NumRotatableBonds(mol)
        }
    except:
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
    except:
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

# Analytics Functions
def train_qsar(data: List[Dict], model_type: str = "random_forest"):
    df = pd.DataFrame(data)
    features = ["molecular_weight", "logp", "tpsa", "hbd", "hba", "rotatable_bonds"]
    df_clean = df[features + ["activity_value"]].dropna()
    
    if len(df_clean) < 10:
        raise ValueError("Need ≥10 compounds")
    
    X = df_clean[features]
    y = df_clean["activity_value"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = RandomForestRegressor(n_estimators=100, random_state=42) if model_type == "random_forest" else LinearRegression()
    model.fit(X_train, y_train)
    
    r2_test = r2_score(y_test, model.predict(X_test))
    rmse_test = np.sqrt(mean_squared_error(y_test, model.predict(X_test)))
    
    importance = pd.DataFrame({
        "feature": features,
        "importance": model.feature_importances_ if model_type == "random_forest" else abs(model.coef_)
    }).sort_values("importance", ascending=False)
    
    return {
        "r2_test": float(r2_test),
        "rmse_test": float(rmse_test),
        "n_samples": len(df_clean),
        "feature_importance": importance.to_dict("records")
    }

def fit_dose_response(conc: List[float], resp: List[float]):
    conc, resp = np.array(conc), np.array(resp)
    mask = ~(np.isnan(conc) | np.isnan(resp))
    conc, resp = conc[mask], resp[mask]
    
    if len(conc) < 5:
        raise ValueError("Need ≥5 points")
    
    def logistic(x, bottom, top, ic50, hill):
        return bottom + (top - bottom) / (1 + (x / ic50) ** hill)
    
    params, _ = curve_fit(
        logistic, conc, resp,
        p0=[np.min(resp), np.max(resp), np.median(conc), 1.0],
        bounds=([0, np.max(resp)*0.5, min(conc)/100, 0.1],
                [np.min(resp)*2, np.inf, max(conc)*100, 10]),
        maxfev=10000
    )
    
    bottom, top, ic50, hill = params
    conc_fit = np.logspace(np.log10(min(conc)/10), np.log10(max(conc)*10), 100)
    resp_fit = logistic(conc_fit, *params)
    
    r2 = 1 - np.sum((resp - logistic(conc, *params))**2) / np.sum((resp - np.mean(resp))**2)
    
    return {
        "ic50": float(ic50),
        "hill_slope": float(hill),
        "top": float(top),
        "bottom": float(bottom),
        "r_squared": float(r2),
        "fitted_curve": {"concentrations": conc_fit.tolist(), "responses": resp_fit.tolist()}
    }

# Routes
@app.get("/")
async def root():
    return {"message": "Lab Informatics API", "version": "1.0.0", "docs": "/docs"}

@app.get("/health")
async def health():
    return {"status": "healthy", "rdkit": RDKIT_AVAILABLE, "mongodb": MONGO_AVAILABLE}

@app.post("/compounds/")
async def create_compound(compound: Compound):
    desc = calculate_descriptors(compound.smiles)
    data = compound.dict()
    data.update(desc)
    data["svg_structure"] = generate_svg(compound.smiles)
    data["lipinski"] = check_lipinski(data)
    data["created_at"] = datetime.now()
    
    if MONGO_AVAILABLE:
        result = compounds_collection.insert_one(data)
        data["_id"] = str(result.inserted_id)
    
    return {"status": "success", "compound": data}

@app.get("/compounds/")
async def list_compounds(limit: int = 50, skip: int = 0):
    if not MONGO_AVAILABLE:
        return {"compounds": [], "total": 0}
    
    compounds = list(compounds_collection.find().skip(skip).limit(limit))
    for c in compounds:
        c["_id"] = str(c["_id"])
    
    return {"compounds": compounds, "total": compounds_collection.count_documents({})}

@app.get("/compounds/{compound_id}")
async def get_compound(compound_id: str):
    if not MONGO_AVAILABLE:
        raise HTTPException(503, "Database unavailable")
    
    try:
        from bson import ObjectId
        compound = compounds_collection.find_one({"_id": ObjectId(compound_id)})
        if not compound:
            raise HTTPException(404, "Not found")
        compound["_id"] = str(compound["_id"])
        return compound
    except:
        raise HTTPException(400, "Invalid ID")

@app.post("/experiments/")
async def create_experiment(exp: Experiment):
    data = exp.dict()
    data["created_at"] = datetime.now()
    if MONGO_AVAILABLE:
        result = experiments_collection.insert_one(data)
        data["_id"] = str(result.inserted_id)
    return {"status": "success", "experiment": data}

@app.get("/experiments/")
async def list_experiments(limit: int = 50, skip: int = 0):
    if not MONGO_AVAILABLE:
        return {"experiments": [], "total": 0}
    
    exps = list(experiments_collection.find().skip(skip).limit(limit))
    for e in exps:
        e["_id"] = str(e["_id"])
    
    return {"experiments": exps, "total": experiments_collection.count_documents({})}

@app.post("/analytics/qsar/train")
async def qsar_train(data: QSARData, model_type: str = "random_forest"):
    try:
        result = train_qsar(data.compounds, model_type)
        return result
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/analytics/dose-response/fit")
async def dose_response_fit(data: DoseResponseData):
    try:
        result = fit_dose_response(data.concentrations, data.responses)
        return result
    except Exception as e:
        raise HTTPException(400, str(e))

@app.post("/similarity/search")
async def similarity_search(smiles: str, threshold: float = 0.7):
    if not RDKIT_AVAILABLE or not MONGO_AVAILABLE:
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
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/analytics/summary")
async def summary():
    if not MONGO_AVAILABLE:
        return {"error": "Database unavailable"}
    
    return {
        "compounds": {"total": compounds_collection.count_documents({})},
        "experiments": {"total": experiments_collection.count_documents({})}
    }
PYTHON_EOF

# ============================================================================
# FRONTEND
# ============================================================================

echo "⚛️  Creating frontend..."

cat > frontend/Dockerfile << 'EOF'
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]
EOF

cat > frontend/package.json << 'EOF'
{
  "name": "lab-frontend",
  "version": "1.0.0",
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  },
  "dependencies": {
    "next": "^14.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  }
}
EOF

cat > frontend/next.config.js << 'EOF'
module.exports = {
  reactStrictMode: true,
}
EOF

cat > frontend/src/pages/index.js << 'EOF'
export default function Home() {
  return (
    <div style={{ padding: '2rem', fontFamily: 'sans-serif', maxWidth: '800px', margin: '0 auto' }}>
      <h1>🧪 Lab Informatics</h1>
      <p>Electronic Lab Notebook for Drug Discovery</p>
      
      <div style={{ marginTop: '2rem', padding: '1.5rem', background: '#f5f5f5', borderRadius: '8px' }}>
        <h2>Quick Start</h2>
        <ol>
          <li>Load sample data: <code>make seed</code></li>
          <li>Explore API: <a href="http://localhost:8000/docs">localhost:8000/docs</a></li>
          <li>Try adding compounds and running analytics</li>
        </ol>
      </div>
      
      <div style={{ marginTop: '2rem' }}>
        <h2>Features</h2>
        <ul>
          <li>Compound library management</li>
          <li>Molecular descriptor calculation (RDKit)</li>
          <li>Similarity searching</li>
          <li>QSAR modeling</li>
          <li>Dose-response curve fitting</li>
          <li>ChEMBL database integration</li>
        </ul>
      </div>
    </div>
  )
}
EOF

# ============================================================================
# SCRIPTS
# ============================================================================

echo "📜 Creating scripts..."

cat > scripts/setup.sh << 'SETUP_EOF'
#!/bin/bash
echo "🧪 Lab Informatics Setup"
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Created .env - edit with your passwords"
else
    echo "✅ .env exists"
fi
chmod +x scripts/*
echo "Next: make start"
SETUP_EOF

cat > scripts/seed_data.py << 'SEED_EOF'
#!/usr/bin/env python3
import requests
import time
import sys

API = "http://localhost:8000"
COMPOUNDS = [
    {"name": "Aspirin", "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O", "tags": ["NSAID"]},
    {"name": "Ibuprofen", "smiles": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O", "tags": ["NSAID"]},
    {"name": "Caffeine", "smiles": "CN1C=NC2=C1C(=O)N(C(=O)N2C)C", "tags": ["stimulant"]},
]

print("Waiting for API...")
for i in range(30):
    try:
        if requests.get(f"{API}/health", timeout=2).status_code == 200:
            print("✅ API ready")
            break
    except:
        pass
    time.sleep(1)
else:
    print("❌ API timeout")
    sys.exit(1)

print("\nLoading compounds...")
for c in COMPOUNDS:
    try:
        r = requests.post(f"{API}/compounds/", json=c)
        print(f"  {'✅' if r.status_code == 200 else '❌'} {c['name']}")
    except Exception as e:
        print(f"  ❌ {c['name']}: {e}")

print("\n✅ Done! Visit http://localhost:3000")
SEED_EOF

chmod +x scripts/*

# ============================================================================
# DOCS
# ============================================================================

echo "📚 Creating docs..."

cat > docs/getting-started.md << 'EOF'
# Getting Started

## Installation

```bash
make setup
# Edit .env
make start
make seed
```

## Usage

Visit http://localhost:8000/docs for full API documentation.

### Add a Compound

```bash
curl -X POST http://localhost:8000/compounds/ \
  -H "Content-Type: application/json" \
  -d '{"name":"Aspirin","smiles":"CC(=O)OC1=CC=CC=C1C(=O)O","tags":["NSAID"]}'
```

### Train QSAR Model

```python
import requests

data = {
    "compounds": [
        {
            "molecular_weight": 180,
            "logp": 1.2,
            "tpsa": 63,
            "hbd": 1,
            "hba": 4,
            "rotatable_bonds": 3,
            "activity_value": 7.5
        }
        # Add more...
    ]
}

r = requests.post("http://localhost:8000/analytics/qsar/train", json=data)
print(f"R²: {r.json()['r2_test']}")
```

### Fit Dose-Response

```python
data = {
    "concentrations": [0.01, 0.1, 1, 10, 100, 1000],
    "responses": [2, 8, 25, 60, 88, 95]
}

r = requests.post("http://localhost:8000/analytics/dose-response/fit", json=data)
print(f"IC50: {r.json()['ic50']}")
```
EOF

cat > docs/examples/qsar-tutorial.md << 'EOF'
# QSAR Tutorial

Train predictive models for compound activity.

## Requirements

- At least 10 compounds with activity data
- Molecular descriptors (auto-calculated)

## Example

```python
import requests

training_data = {
    "compounds": [
        {
            "molecular_weight": 180.16,
            "logp": 1.19,
            "tpsa": 63.6,
            "hbd": 1,
            "hba": 4,
            "rotatable_bonds": 3,
            "activity_value": 7.5  # pIC50
        },
        # ... add 9+ more compounds
    ]
}

response = requests.post(
    "http://localhost:8000/analytics/qsar/train?model_type=random_forest",
    json=training_data
)

result = response.json()
print(f"Test R²: {result['r2_test']:.3f}")
print(f"RMSE: {result['rmse_test']:.3f}")
print("\nTop features:")
for feat in result['feature_importance'][:3]:
    print(f"  {feat['feature']}: {feat['importance']:.3f}")
```

## Interpretation

- R² > 0.7: Good predictive model
- Check feature importance for SAR insights
- Validate with external test set
EOF

# ============================================================================
# FINALIZE
# ============================================================================

cd ..

echo ""
echo "========================================="
echo "✅ PROJECT GENERATED SUCCESSFULLY!"
echo "========================================="
echo ""
echo "Location: $(pwd)/$PROJECT_NAME"
echo ""
echo "Next steps:"
echo ""
echo "  cd $PROJECT_NAME"
echo "  make setup"
echo "  # Edit .env with your passwords"
echo "  make start"
echo "  make seed"
echo ""
echo "Then visit:"
echo "  Frontend: http://localhost:3000"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "🎉 Happy drug discovery!"
echo ""