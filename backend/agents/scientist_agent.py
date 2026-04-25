"""
Lab Scientist Agent

Orchestrates the full simulation-to-ELN pipeline:
  1. Runs a lab-data-simulator instrument to generate realistic data
  2. Analyzes the results (IC50, KD, purity, population stats)
  3. Calls a local Ollama LLM (mistral:7b by default) to write scientific narrative
  4. Assembles a fully-structured ELN entry
  5. POSTs it to the lab-informatics /eln/ API

The agent keeps lab-data-simulator and lab-informatics as independent repos:
it talks to the ELN via HTTP, not direct DB access.

Usage:
  from agents.scientist_agent import LabScientistAgent
  agent = LabScientistAgent()
  result = await agent.run(experiment_type="dose_response")
"""

import os
import random
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Literal
import requests
from sqlalchemy.orm import Session
from api.postgres import get_db, User
from api.services import eln_service
from models.schemas import ELNEntry

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral:7b")
ELN_API_URL = os.getenv("ELN_API_URL", "http://localhost:8000")
AGENT_JWT_TOKEN = os.getenv(
    "AGENT_JWT_TOKEN", ""
)  # Service account token for auto-posting

ExperimentType = Literal["dose_response", "spr", "purity", "flow", "hci"]

# Simulated scientist personas the agent cycles through
SCIENTIST_PERSONAS = [
    {
        "username": "agent_scientist",
        "full_name": "AI Lab Scientist",
        "title": "Research Scientist I",
    },
]

# Compound pools the agent will choose from
COMPOUND_POOL = [
    {
        "compound_id": "CMP-001",
        "compound_name": "Staurosporine",
        "source_well": "A1",
        "concentration": 10000,
    },
    {
        "compound_id": "CMP-002",
        "compound_name": "Gefitinib",
        "source_well": "A2",
        "concentration": 10000,
    },
    {
        "compound_id": "CMP-003",
        "compound_name": "Imatinib",
        "source_well": "A3",
        "concentration": 10000,
    },
    {
        "compound_id": "CMP-004",
        "compound_name": "Erlotinib",
        "source_well": "A4",
        "concentration": 10000,
    },
    {
        "compound_id": "CMP-005",
        "compound_name": "Lapatinib",
        "source_well": "A5",
        "concentration": 10000,
    },
    {
        "compound_id": "DMSO",
        "compound_name": "DMSO Control",
        "source_well": "P1",
        "concentration": 0,
    },
]


class LabScientistAgent:
    """AI scientist that generates lab data and writes ELN entries."""

    def __init__(self):
        self._simulator_available = self._check_simulator()
        self._ollama_available = self._check_ollama()
        self.last_run: Optional[dict] = None

    # ── Availability checks ───────────────────────────────────────────────────

    def _check_simulator(self) -> bool:
        try:
            from lab_data_simulator.simulators import PlateReader, SPRSimulator

            return True
        except ImportError as e:
            logger.warning(f"lab-data-simulator not available: {e}")
            return False

    def _check_ollama(self) -> bool:
        try:
            resp = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=3)
            return resp.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama not reachable at {OLLAMA_HOST}: {e}")
            return False

    # ── Simulation ────────────────────────────────────────────────────────────

    def _simulate_dose_response(self) -> dict:
        """Run an Echo + PHERAstar simulation pipeline."""
        from lab_data_simulator.simulators import Echo, PheraSTAR

        compounds = random.sample(COMPOUND_POOL[:-1], k=min(3, len(COMPOUND_POOL) - 1))
        compounds.append(COMPOUND_POOL[-1])  # always include DMSO

        echo = Echo(seed=random.randint(0, 9999))
        picklist = echo.make_dose_response_picklist(
            compounds=compounds,
            source_plate=f"SRC_{uuid.uuid4().hex[:6].upper()}",
            dest_plate=f"ASSAY_{uuid.uuid4().hex[:6].upper()}",
            top_vol_nl=250.0,
            dilution_factor=3.0,
            n_points=8,
            n_replicates=2,
            failure_rate=0.05,
            volume_cv=0.03,
        )

        ground_truth = {}
        ic50_results = {}
        for cpd in compounds:
            cid = cpd["compound_id"]
            if cid == "DMSO":
                ground_truth[cid] = {
                    "a": 50000,
                    "b": 1.0,
                    "c": 1.0,
                    "d": 50000,
                    "noise": 800,
                }
            else:
                ic50 = round(random.uniform(0.05, 20.0), 3)
                ic50_results[cid] = ic50
                ground_truth[cid] = {
                    "a": round(random.uniform(5, 15), 1),
                    "b": round(random.uniform(0.8, 1.5), 2),
                    "c": ic50,
                    "d": 50000,
                    "noise": random.randint(800, 2000),
                }

        reader = PheraSTAR()
        result_df = reader.run_simulation(
            {
                "mode": "picklist_driven",
                "params": {
                    "picklist": picklist,
                    "ground_truth": ground_truth,
                    "assay_volume_nl": 50000.0,
                    "baseline": 100,
                    "baseline_noise": 20,
                },
            }
        )

        return {
            "type": "dose_response",
            "compounds": [
                c["compound_name"] for c in compounds if c["compound_id"] != "DMSO"
            ],
            "compound_details": compounds,
            "ic50_results": ic50_results,
            "n_datapoints": len(result_df),
            "plate_id": ground_truth and list(ground_truth.keys())[0],
            "raw_summary": {
                "mean_signal": (
                    float(result_df["signal"].mean())
                    if "signal" in result_df.columns
                    else None
                ),
                "n_wells": len(result_df),
                "n_failed_transfers": (
                    int((picklist["transfer_status"] == "FAILED").sum())
                    if "transfer_status" in picklist.columns
                    else 0
                ),
            },
        }

    def _simulate_spr(self) -> dict:
        """Run an SPR binding kinetics simulation."""
        from lab_data_simulator.simulators import SPRSimulator

        compounds = random.sample([c["compound_id"] for c in COMPOUND_POOL[:-1]], k=3)
        spr = SPRSimulator()
        results_df = spr.run_simulation({"samples": compounds})

        kd_results = {}
        if results_df is not None and not results_df.empty:
            for _, row in results_df.iterrows():
                cid = row.get("compound_id", row.get("sample", "unknown"))
                kd_results[str(cid)] = {
                    "KD_nM": float(row.get("KD_nM", row.get("KD", 0))),
                    "kon": float(row.get("kon", 0)),
                    "koff": float(row.get("koff", 0)),
                }

        return {
            "type": "spr",
            "compounds": compounds,
            "kd_results": kd_results,
            "target": random.choice(["EGFR", "BRAF", "CDK2", "PI3K", "AKT"]),
        }

    def _simulate_purity(self) -> dict:
        """Run a compound purity analysis simulation."""
        from lab_data_simulator.simulators import PuritySimulator

        compounds = random.sample([c["compound_id"] for c in COMPOUND_POOL[:-1]], k=4)
        purity_sim = PuritySimulator()
        results_df = purity_sim.run_simulation({"samples": compounds})

        purity_results = {}
        if results_df is not None and not results_df.empty:
            for _, row in results_df.iterrows():
                cid = str(row.get("compound_id", row.get("sample", "unknown")))
                purity_results[cid] = float(
                    row.get("purity_pct", row.get("purity", 95))
                )

        return {
            "type": "purity",
            "compounds": compounds,
            "purity_results": purity_results,
        }

    def _simulate_flow(self) -> dict:
        """Run a flow cytometry simulation."""
        from lab_data_simulator.simulators import FlowCytometrySimulator

        flow = FlowCytometrySimulator()
        compounds = random.sample([c["compound_id"] for c in COMPOUND_POOL[:-1]], k=2)
        results_df = flow.run_simulation({"samples": compounds})

        population_results = {}
        if results_df is not None and not results_df.empty:
            for _, row in results_df.iterrows():
                cid = str(row.get("compound_id", row.get("sample", "unknown")))
                population_results[cid] = {
                    "live_pct": float(row.get("live_pct", row.get("viability", 85))),
                    "apoptotic_pct": float(
                        row.get("apoptotic_pct", row.get("apoptosis", 10))
                    ),
                }

        return {
            "type": "flow_cytometry",
            "compounds": compounds,
            "population_results": population_results,
            "marker": random.choice(["Annexin V/PI", "Caspase-3/7", "Ki67"]),
        }

    def simulate(self, experiment_type: ExperimentType) -> dict:
        """Dispatch to the correct simulator."""
        if not self._simulator_available:
            return self._mock_simulation(experiment_type)
        try:
            if experiment_type == "dose_response":
                return self._simulate_dose_response()
            elif experiment_type == "spr":
                return self._simulate_spr()
            elif experiment_type == "purity":
                return self._simulate_purity()
            elif experiment_type == "flow":
                return self._simulate_flow()
            else:
                return self._mock_simulation(experiment_type)
        except Exception as e:
            logger.error(f"Simulation failed ({experiment_type}): {e}")
            return self._mock_simulation(experiment_type)

    def _mock_simulation(self, experiment_type: ExperimentType) -> dict:
        """Fallback mock data when simulator is not installed."""
        compounds = ["Staurosporine", "Gefitinib", "Imatinib"]
        if experiment_type == "dose_response":
            return {
                "type": "dose_response",
                "compounds": compounds[:2],
                "ic50_results": {"CMP-001": 0.23, "CMP-002": 4.7},
                "n_datapoints": 64,
                "raw_summary": {
                    "mean_signal": 28456.0,
                    "n_wells": 96,
                    "n_failed_transfers": 2,
                },
                "mock": True,
            }
        elif experiment_type == "spr":
            return {
                "type": "spr",
                "compounds": ["CMP-001", "CMP-002"],
                "kd_results": {
                    "CMP-001": {"KD_nM": 12.4, "kon": 1.2e5, "koff": 1.5e-3},
                    "CMP-002": {"KD_nM": 890.0, "kon": 4.5e4, "koff": 4.0e-2},
                },
                "target": "EGFR",
                "mock": True,
            }
        return {"type": experiment_type, "compounds": compounds, "mock": True}

    # ── LLM Narrative ─────────────────────────────────────────────────────────

    def _build_prompt(self, experiment_data: dict, analysis: dict, author: str) -> str:
        exp_type = experiment_data.get("type", "experiment")
        compounds = ", ".join(experiment_data.get("compounds", []))

        if exp_type == "dose_response":
            key_findings = "; ".join(
                [
                    f"{cid}: IC50 = {v:.3f} µM"
                    for cid, v in analysis.get("ic50_results", {}).items()
                ]
            )
            objective = f"Determine potency (IC50) of {compounds} in a 384-well biochemical assay"
        elif exp_type == "spr":
            key_findings = "; ".join(
                [
                    f"{cid}: KD = {v['KD_nM']:.1f} nM"
                    for cid, v in analysis.get("kd_results", {}).items()
                ]
            )
            target = experiment_data.get("target", "target protein")
            objective = f"Measure binding kinetics of {compounds} to {target} by SPR"
        elif exp_type == "purity":
            key_findings = "; ".join(
                [
                    f"{cid}: {v:.1f}% purity"
                    for cid, v in analysis.get("purity_results", {}).items()
                ]
            )
            objective = f"Assess compound purity of {compounds} by HPLC-UV"
        elif exp_type == "flow_cytometry":
            key_findings = "; ".join(
                [
                    f"{cid}: {v['live_pct']:.1f}% viability"
                    for cid, v in analysis.get("population_results", {}).items()
                ]
            )
            objective = f"Assess cellular viability and apoptosis for {compounds}"
        else:
            key_findings = str(analysis)
            objective = f"Conduct {exp_type} analysis on {compounds}"

        return f"""You are a research scientist writing an entry in an electronic lab notebook (ELN) for a drug discovery project.
Write professional, concise scientific prose for the following sections. Use past tense. Be specific with data.

Experiment type: {exp_type.replace('_', ' ').title()}
Compounds tested: {compounds}
Objective: {objective}
Key findings: {key_findings}
Author: {author}

Write exactly 3 sections delimited by XML tags:

<procedure>
2-3 sentences describing the experimental procedure performed. Include instrument used, key assay parameters, and controls.
</procedure>

<observations>
2-3 sentences describing what was observed during the experiment. Reference specific data points from the key findings.
</observations>

<conclusion>
1-2 sentences summarizing the scientific conclusion and next steps.
</conclusion>

Do not include any text outside these XML tags."""

    def _call_ollama(self, prompt: str) -> str:
        """Call the Ollama API and return generated text."""
        try:
            import ollama as ollama_client

            response = ollama_client.chat(
                model=OLLAMA_MODEL,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.4, "num_predict": 512},
            )
            return response["message"]["content"]
        except Exception as e:
            logger.warning(f"Ollama call failed: {e}. Using fallback template.")
            return self._fallback_narrative(prompt)

    def _fallback_narrative(self, prompt: str) -> str:
        """Template-based fallback when Ollama is unavailable."""
        return (
            "<procedure>The experiment was conducted according to standard operating procedures "
            "using validated instruments. Appropriate controls were included on each plate.</procedure>"
            "<observations>All data points were within expected range. Key results are documented "
            "in the results section.</observations>"
            "<conclusion>The experiment was completed successfully. Results will be reviewed and "
            "incorporated into the lead selection decision.</conclusion>"
        )

    def _parse_sections(self, narrative: str) -> list:
        """Extract XML-tagged sections from LLM output."""
        import re

        sections = []
        tags = [
            ("procedure", "Experimental Procedure"),
            ("observations", "Observations"),
            ("conclusion", "Conclusion"),
        ]
        for tag, title in tags:
            match = re.search(rf"<{tag}>(.*?)</{tag}>", narrative, re.DOTALL)
            content = match.group(1).strip() if match else f"[{title} not generated]"
            sections.append(
                {
                    "section_id": str(uuid.uuid4()),
                    "section_type": tag if tag != "observations" else "observation",
                    "title": title,
                    "content": content,
                }
            )
        return sections

    # ── ELN Assembly ──────────────────────────────────────────────────────────

    def _analyze(self, sim_data: dict) -> dict:
        """Extract key quantitative results from simulation data."""
        return {
            "ic50_results": sim_data.get("ic50_results", {}),
            "kd_results": sim_data.get("kd_results", {}),
            "purity_results": sim_data.get("purity_results", {}),
            "population_results": sim_data.get("population_results", {}),
        }

    def _build_eln_entry(
        self,
        sim_data: dict,
        analysis: dict,
        narrative: str,
        author_name: str,
        author_title: str,
    ) -> dict:
        exp_type = sim_data.get("type", "experiment")
        compounds = sim_data.get("compounds", [])
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        title_map = {
            "dose_response": f"Dose-Response Assay — {', '.join(compounds[:2])} — {date_str}",
            "spr": f"SPR Binding Kinetics — {', '.join(compounds[:2])} — {date_str}",
            "purity": f"Purity Analysis — {', '.join(compounds[:2])} — {date_str}",
            "flow_cytometry": f"Flow Cytometry Viability — {', '.join(compounds[:2])} — {date_str}",
        }

        sections = self._parse_sections(narrative)

        # Add a results section with structured data
        results_content = self._format_results(sim_data, analysis)
        sections.append(
            {
                "section_id": str(uuid.uuid4()),
                "section_type": "result",
                "title": "Quantitative Results",
                "content": results_content,
            }
        )

        return {
            "title": title_map.get(exp_type, f"{exp_type.title()} — {date_str}"),
            "author": author_name,
            "author_title": author_title,
            "objective": f"AI-simulated {exp_type.replace('_', ' ')} experiment using lab-data-simulator",
            "sections": sections,
            "tags": ["agent-generated", exp_type, "simulation"] + compounds[:3],
        }

    def _format_results(self, sim_data: dict, analysis: dict) -> str:
        lines = []
        exp_type = sim_data.get("type", "")
        if exp_type == "dose_response" and analysis.get("ic50_results"):
            lines.append("IC50 Results:")
            for cid, ic50 in analysis["ic50_results"].items():
                lines.append(f"  {cid}: {ic50:.3f} µM")
        elif exp_type == "spr" and analysis.get("kd_results"):
            lines.append(f"Target: {sim_data.get('target', 'N/A')}")
            lines.append("Binding Kinetics:")
            for cid, kd in analysis["kd_results"].items():
                lines.append(
                    f"  {cid}: KD = {kd['KD_nM']:.1f} nM, kon = {kd['kon']:.2e}, koff = {kd['koff']:.2e}"
                )
        elif exp_type == "purity" and analysis.get("purity_results"):
            lines.append("Purity Results:")
            for cid, p in analysis["purity_results"].items():
                lines.append(f"  {cid}: {p:.1f}%")
        elif exp_type == "flow_cytometry" and analysis.get("population_results"):
            lines.append("Cell Population Results:")
            for cid, pop in analysis["population_results"].items():
                lines.append(
                    f"  {cid}: {pop['live_pct']:.1f}% viable, {pop['apoptotic_pct']:.1f}% apoptotic"
                )
        else:
            lines.append("See experiment data for full results.")
        lines.append(
            f"\nData source: lab-data-simulator | Generated: {datetime.now(timezone.utc).isoformat()}"
        )
        if sim_data.get("mock"):
            lines.append(
                "⚠️  Note: Generated with mock data (lab-data-simulator not installed in this environment)."
            )
        return "\n".join(lines)

    # ── Post to ELN ───────────────────────────────────────────────────────────

    def _post_to_eln(self, entry_dict: dict, token: str) -> dict:
        """
        POSTs the ELN entry.

        Logic:
          - If the agent is running inside the backend process (has access to eln_service),
            it calls the service directly to avoid deadlocking the single-threaded server.
          - Otherwise, it falls back to HTTP.
        """
        try:
            # 1. Try In-Process Service (Prevents Deadlock)
            db_gen = get_db()
            db_session: Session = next(db_gen)

            # Find the user record for the agent
            agent_user = (
                db_session.query(User)
                .filter(User.username == entry_dict["author"])
                .first()
            )

            if agent_user:
                logger.info(
                    f"Agent: Saving entry via in-process service for {agent_user.username}"
                )
                # Re-validate as ELNEntry schema
                entry_schema = ELNEntry(**entry_dict)
                saved_entry = eln_service.create_entry(entry_schema, agent_user)
                return {"status": "success", "entry": saved_entry}

        except Exception as e:
            logger.warning(f"In-process save failed, falling back to HTTP: {e}")

        # 2. Fallback to HTTP (will likely timeout if running in single-threaded process)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        resp = requests.post(
            f"{ELN_API_URL}/eln/", json=entry_dict, headers=headers, timeout=10
        )
        resp.raise_for_status()
        return resp.json()

    # ── Main pipeline ─────────────────────────────────────────────────────────

    def run(
        self,
        experiment_type: ExperimentType = "dose_response",
        author_name: str = "agent_scientist",
        author_title: str = "AI Research Scientist",
        token: str = "",
    ) -> dict:
        """
        Full pipeline: simulate → analyze → write narrative → post to ELN.
        Returns a status dict with the created entry or error info.
        """
        start = datetime.now(timezone.utc)
        result = {
            "status": "running",
            "experiment_type": experiment_type,
            "started_at": start.isoformat(),
            "simulator_available": self._simulator_available,
            "ollama_available": self._ollama_available,
        }

        try:
            # 1. Simulate
            logger.info(f"Agent: simulating {experiment_type}")
            sim_data = self.simulate(experiment_type)
            result["simulation"] = {
                "type": sim_data["type"],
                "compounds": sim_data.get("compounds", []),
            }

            # 2. Analyze
            analysis = self._analyze(sim_data)
            result["analysis"] = analysis

            # 3. Generate narrative via Ollama
            logger.info("Agent: generating ELN narrative via Ollama")
            prompt = self._build_prompt(sim_data, analysis, author_name)
            narrative = self._call_ollama(prompt)
            result["narrative_generated"] = True

            # 4. Assemble ELN entry
            entry = self._build_eln_entry(
                sim_data, analysis, narrative, author_name, author_title
            )

            # 5. Post to ELN API (only if token provided)
            use_token = token or AGENT_JWT_TOKEN
            if use_token:
                eln_response = self._post_to_eln(entry, use_token)
                result["eln_entry"] = eln_response.get("entry", {})
                result["entry_id"] = eln_response.get("entry", {}).get("entry_id")
                result["posted"] = True
            else:
                result["entry"] = entry
                result["posted"] = False
                result["note"] = (
                    "Set AGENT_JWT_TOKEN env var or pass token= to auto-post to ELN"
                )

            result["status"] = "success"
        except Exception as e:
            logger.error(f"Agent run failed: {e}", exc_info=True)
            result["status"] = "error"
            result["error"] = str(e)

        result["completed_at"] = datetime.now(timezone.utc).isoformat()
        self.last_run = result
        return result
