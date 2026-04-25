# Module 03: Agentic AI in the Laboratory

## What "Agent" Means Here

The term "agent" is used broadly in AI. In this project it refers to a program that **perceives** data, **decides** on an action, **executes** it, and **records** the outcome.

The **Lab Scientist Agent** implements a linear pipeline:

```
1. Select experiment type (dose_response, spr, purity, flow)
        │
        ▼
2. Generate simulated instrument data (via lab-data-simulator)
        │
        ▼
3. Analyze data — curve fitting, IC50/KD calculation
        │
        ▼
4. Generate a written narrative (via local LLM)
        │
        ▼
5. Assemble narrative + results into an ELN entry
        │
        ▼
6. Persist the entry via the ELN service layer
```

This is a single-pass pipeline, not a feedback loop. A more sophisticated agent would evaluate its output and iterate.

---

## 1. Simulating Instrument Data

Real instruments are expensive, and pharmaceutical data is proprietary. The `lab-data-simulator` repository generates synthetic datasets that approximate real assay outputs — including noise and outliers.

| Simulator | Output | Lab Use |
|---|---|---|
| Echo Liquid Handler | Dose-response matrices | Compound dispensing |
| PHERAstar Plate Reader | 4PL response curves | Biochemical screening |
| SPR (Biacore-like) | Kinetics (KD, kon, koff) | Affinity characterization |
| Flow Cytometer | Cell population percentages | Viability assays |
| HPLC-UV | Purity percentages | Quality control |

**Trade-off:** Simulated data reproduces the mathematical shape of real responses but not their full complexity (edge effects, reagent degradation, operator variability). The simulator exercises the data pipeline, not biological conclusions.

---

## 2. Cross-Repository Integration

The simulator lives in a separate repository. Integration uses a Docker volume mount with an editable pip install:

```yaml
# docker-compose.yml
backend:
  volumes:
    - ./backend:/app
    - ../lab-data-simulator:/lab-data-simulator
```

```dockerfile
# backend/Dockerfile
RUN if [ -d /lab-data-simulator ]; then pip install -e /lab-data-simulator; fi
```

This lets the backend `import lab_data_simulator` and reflects host-side edits immediately.

**Trade-off:** Editable volume mounts are a local development convenience. In production, the simulator would be versioned and published to a package registry.

---

## 3. The 4-Parameter Logistic (4PL) Model

Dose-response data follows a sigmoidal curve. The standard fitting model is:

```
Response = d + (a − d) / (1 + (c / concentration)^b)
```

| Parameter | Meaning |
|---|---|
| **a** | Lower asymptote (baseline) |
| **d** | Upper asymptote (max response) |
| **b** | Hill slope (steepness) |
| **c** | IC₅₀ (concentration at 50% effect) |

The simulator generates noisy data points along this curve. The backend recovers the parameters via nonlinear least-squares regression (`scipy.optimize.curve_fit`). The IC₅₀ is the primary pharmacological output: lower IC₅₀ = more potent compound.

---

## 4. Local LLM Execution with Ollama

**Ollama** runs Large Language Models locally. In pharmaceutical settings, sending proprietary data to third-party APIs raises IP and data governance concerns. Local execution eliminates that exposure.

This project uses `mistral:7b` (7 billion parameters, ~4–6 GB RAM). It runs on a standard laptop without a GPU, but inference is slow (30–90 seconds per generation).

```python
import ollama as ollama_client

response = ollama_client.chat(
    model="mistral:7b",
    messages=[{"role": "user", "content": prompt}],
    options={"temperature": 0.4},
)
narrative = response["message"]["content"]
```

Low `temperature` (0.4) biases toward high-probability tokens — more deterministic, less hallucination. Higher values increase creativity but risk fabricating facts in scientific records.

**Trade-off:** Local inference is private but resource-constrained. A 7B model produces adequate structured text for notebook narratives, but its reasoning is limited compared to larger models or cloud APIs.

---

## 5. Prompt Engineering for Structured Output

The agent needs the LLM to produce parseable sections. The prompt uses XML tags as delimiters:

```python
def _build_prompt(self, experiment_data, analysis, author):
    return f"""You are a research scientist writing an ELN entry.
Write exactly 3 sections delimited by XML tags:

Experiment type: {exp_type}
Findings: {key_findings}

<procedure>
2-3 sentences describing the procedure.
</procedure>

<observations>
2-3 sentences summarizing observations.
</observations>
"""
```

XML tags are unambiguous delimiters extractable with a simple regex, even when the content between them is free-form text.

---

## 6. Graceful Degradation

The agent falls back when optional dependencies are unavailable:

```python
def simulate(self, experiment_type):
    if not self._simulator_available:
        return self._mock_simulation(experiment_type)
    try:
        return self._simulate_dose_response()
    except Exception:
        return self._mock_simulation(experiment_type)
```

- No simulator installed → agent generates minimal mock data internally.
- Ollama not running → agent uses a static text template instead of LLM output.

This allows the ELN creation, hashing, and signing flows to be exercised even without the AI components.

---

## Exercises

### Exercise 3.1: Interact with the LLM Directly

```bash
ollama pull mistral:7b
ollama run mistral:7b "Write a two-sentence procedure for a dose-response assay."
```

Modify the prompt to request passive voice, then active voice. Note how output varies with prompt phrasing.

### Exercise 3.2: Run the Full Agent Pipeline

1. Navigate to `http://localhost:3000/agent`.
2. Select **Dose-Response** and click **Run Simulation**.
3. Wait 30–90 seconds. Observe the IC50 values.
4. Click **View ELN Entry** to inspect the LLM-generated narrative.

### Exercise 3.3: Explore the Simulator API

```python
import sys
sys.path.insert(0, '/lab-data-simulator/src')
from lab_data_simulator.simulators import Echo

echo = Echo(seed=42)
compounds = [{'compound_id': 'CMP-001', 'concentration': 10000}]
picklist = echo.make_dose_response_picklist(
    compounds=compounds, source_plate='SRC_001', dest_plate='ASSAY_001'
)
print(picklist.head())
```

Experiment with the `failure_rate` parameter to observe how instrument errors propagate through the data.
