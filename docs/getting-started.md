# Getting Started

## Prerequisites

- **Docker Desktop** (includes `docker-compose`)
- **Ollama** (for the AI Scientist agent) — https://ollama.com
- A terminal and a web browser

---

## Installation

```bash
# 1. Clone the repo
git clone https://github.com/jababu3/lab-informatics.git
cd lab-informatics

# 2. Copy the environment template
cp .env.example .env
```

Open `.env` and update these values:
```bash
JWT_SECRET_KEY=some-long-random-string-here   # IMPORTANT: change this!
MONGO_PASSWORD=your-password
POSTGRES_PASSWORD=your-password
```

```bash
# 3. Start the stack
docker-compose up --build
```

Visit http://localhost:3000 — you'll see the dashboard.

---

## Create Your First Account

Go to **http://localhost:3000/register**

Fill in:
- Your full name and title (e.g. "Dr. Jane Smith" / "Principal Investigator")
- A username, email, and password

The first registered user automatically gets the **admin** role.

After registering, you'll be logged in and redirected to the home page.

---

## Set Up the AI Scientist (Optional but Recommended)

```bash
# 1. Install Ollama
# Mac: https://ollama.com/download
# Then pull the model (4.5 GB download, one time):
ollama pull mistral:7b

# 2. Install lab-data-simulator into the backend container
docker-compose exec backend pip install -e /lab-data-simulator
```

Then visit **http://localhost:3000/agent** and click **Run Simulation**.

---

## Explore the API Interactively

The API has a built-in Swagger UI — no code needed to try any endpoint:

**http://localhost:8000/docs**

To authenticate in the Swagger UI:
1. Call `POST /auth/login` with your username and password
2. Copy the `access_token` from the response
3. Click **Authorize** (top right) and paste the token
4. All subsequent requests will include your JWT

---

## Add a Compound

### Via the frontend:
Go to http://localhost:3000/compounds → "Add Compound"

### Via the API:
```bash
curl -X POST http://localhost:8000/compounds/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Imatinib",
    "smiles": "Cc1ccc(NC(=O)c2ccc(CN3CCN(C)CC3)cc2)cc1Nc1nccc(-c2cccnc2)n1",
    "tags": ["kinase-inhibitor", "BCR-ABL"]
  }'
```

RDKit will automatically compute molecular weight, LogP, hydrogen bond donors/acceptors, and Lipinski compliance.

---

## Run an Analytics Workflow

### Dose-response curve fitting:

```python
import requests

# Measured signal at 8 concentrations
data = {
    "concentrations": [0.001, 0.01, 0.1, 1, 10, 100, 1000, 10000],
    "responses":      [2, 3, 12, 45, 78, 91, 96, 97]
}

r = requests.post("http://localhost:8000/analytics/dose-response/fit", json=data)
result = r.json()

print(f"IC50: {result['ic50']} µM")
print(f"Hill slope: {result['hill_slope']}")
print(f"R²: {result['r_squared']:.4f}")
```

### QSAR model training:

```python
data = {
    "compounds": [
        {"molecular_weight": 180, "logp": 1.2, "tpsa": 63,
         "hbd": 1, "hba": 4, "rotatable_bonds": 3, "activity_value": 7.5},
        {"molecular_weight": 250, "logp": 2.1, "tpsa": 45,
         "hbd": 2, "hba": 3, "rotatable_bonds": 5, "activity_value": 6.2},
        # Add more compounds for better model performance...
    ]
}

r = requests.post("http://localhost:8000/analytics/qsar/train", json=data)
print(f"R² (test set): {r.json()['r2_test']:.4f}")
```

---

## Create an ELN Entry Manually

```bash
# First, log in and get a token
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=jsmith&password=yourpassword" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Create an ELN entry (requires authentication)
curl -X POST http://localhost:8000/eln/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Imatinib IC50 in BCR-ABL Kinase Assay",
    "author": "jsmith",
    "author_title": "Research Scientist I",
    "objective": "Determine potency of imatinib against BCR-ABL",
    "sections": [
      {
        "section_id": "s1",
        "section_type": "procedure",
        "title": "Experimental Procedure",
        "content": "Imatinib was tested at 8 concentrations (0.001–10000 µM) in triplicate using a 384-well biochemical kinase assay."
      }
    ],
    "tags": ["BCR-ABL", "kinase", "imatinib"]
  }'
```

---

## Sign an ELN Entry (21 CFR Part 11)

```bash
# Sign the entry (your JWT identity must match signer_name)
curl -X POST http://localhost:8000/eln/{entry_id}/sign \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "signer_name": "jsmith",
    "signer_title": "Research Scientist I",
    "meaning": "Author approval — I confirm this record is accurate",
    "acknowledgment_text": ""
  }'
```

After signing, the entry is **locked** — no further edits are permitted.

---

## Common Commands

```bash
# View logs
docker-compose logs -f backend

# Restart the backend (picks up code changes automatically)
docker-compose restart backend

# Open a Python shell inside the container
docker-compose exec backend python

# Reset everything (WARNING: deletes all data)
docker-compose down -v && docker-compose up --build

# Load sample compound data
make seed
```

---

## Troubleshooting

**Postgres won't connect at startup**  
Wait ~10 seconds after `docker-compose up` — Postgres takes a moment to initialize. The backend retries on startup.

**`lab-data-simulator` import fails**  
```bash
docker-compose exec backend pip install -e /lab-data-simulator
```

**Ollama model not available**  
Make sure Ollama is running on your host: `ollama serve`  
Then on Mac/Windows, `host.docker.internal` resolves to your laptop. On Linux, the `extra_hosts` directive in docker-compose handles this.

**JWT not working in API docs**  
In Swagger (`/docs`), use the `Authorize` button and set the value to just the token (without "Bearer "). FastAPI adds the prefix automatically.
