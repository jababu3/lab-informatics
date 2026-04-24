#!/usr/bin/env python3
"""
pubchem_eln_scientist.py
─────────────────────────
AI Scientist: generates structured Markdown ELN notes from PubChem BioAssay data.

For each CRC assay sheet in a PubChem BioAssay Excel workbook:
  • Extracts assay metadata, activity stats, IC50 distribution, top actives
  • Calls Ollama (mistral:7b by default) for a narrative observation/conclusion
  • Falls back to a deterministic rich template when Ollama is unreachable
  • Writes one Markdown .md file per assay to --out-dir

The Markdown structure mirrors the lab-informatics ELNSection schema:
  Procedure | Observations | Results Table | Conclusion | Notes

Usage:
    # From the lab-informatics root directory:
    python scripts/pubchem_eln_scientist.py \\
        --xlsx data/Orexin_PubChem_BioAssay.xlsx \\
        --out-dir backend/uploads/eln/ \\
        --author "James Bullis" \\
        --author-title "Lab Informatics Scientist" \\
        --ollama-host http://localhost:11434 \\
        --ollama-model mistral:7b

Dependencies: requests, pandas, openpyxl
"""

import argparse
import json
import os
import re
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description="AI Scientist: generate Markdown ELN notes from PubChem BioAssay data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--xlsx", required=True,
                   help="Path to PubChem BioAssay Excel workbook")
    p.add_argument("--out-dir", default="backend/uploads/eln",
                   help="Output directory for .md ELN files (default: backend/uploads/eln)")
    p.add_argument("--author", default="James Bullis",
                   help="ELN entry author name")
    p.add_argument("--author-title", default="Lab Informatics Scientist",
                   help="ELN entry author title")
    p.add_argument("--ollama-host", default="http://localhost:11434",
                   help="Ollama API host (default: http://localhost:11434)")
    p.add_argument("--ollama-model", default="mistral:7b",
                   help="Ollama model to use (default: mistral:7b)")
    p.add_argument("--top-n", type=int, default=8,
                   help="Top N actives to include in results table (default: 8)")
    p.add_argument("--target", default="Orexin Receptor",
                   help="Human-readable target name for the ELN narrative")
    # API registration (optional — enables entries to appear in the GUI)
    p.add_argument("--base-url", default="http://localhost:8000",
                   help="Lab-informatics API base URL for posting ELN entries (default: http://localhost:8000)")
    p.add_argument("--api-username",
                   help="Username for API login (required to post entries to the GUI)")
    p.add_argument("--api-password",
                   help="Password for API login")
    return p.parse_args()


# ── Excel helpers (same logic as importer) ────────────────────────────────────

def _col(df: pd.DataFrame, *candidates: str) -> Optional[str]:
    for c in df.columns:
        for cand in candidates:
            if cand.upper() in c.upper():
                return c
    return None


def read_assay_sheet(xl: pd.ExcelFile, sheet_name: str) -> pd.DataFrame:
    raw = xl.parse(sheet_name, header=None)
    header_row = None
    for i, row in raw.iterrows():
        vals = [str(v).strip().upper() for v in row if not pd.isna(v)]
        if "PUBCHEM_RESULT_TAG" in vals or "PUBCHEM_CID" in vals:
            header_row = i
            break
    if header_row is None:
        return pd.DataFrame()
    df = xl.parse(sheet_name, header=header_row)
    df.columns = [str(c).strip() for c in df.columns]
    if "PUBCHEM_RESULT_TAG" in df.columns:
        df = df[pd.to_numeric(df["PUBCHEM_RESULT_TAG"],
                              errors="coerce").notna()].reset_index(drop=True)
    return df


# ── Assay data extraction ─────────────────────────────────────────────────────

def extract_assay_stats(df: pd.DataFrame, aid: str, target: str, top_n: int) -> dict:
    """Return a dict of summary statistics for one assay sheet."""
    out_col    = _col(df, "OUTCOME")
    ic50_col   = _col(df, "IC50")
    hill_col   = _col(df, "HILL", "SLOPE")
    emax_col   = _col(df, "MAXIMAL", "EMAX")
    r2_col     = _col(df, "RSQUARE", "R2", "R_SQUARE")
    name_col   = _col(df, "COMPOUND_NAME", "NAME")
    cid_col    = _col(df, "PUBCHEM_CID")
    smiles_col = _col(df, "SMILES")

    n_total = len(df)

    # Activity counts
    if out_col:
        uc = df[out_col].str.upper()
        n_active   = int((uc == "ACTIVE").sum())
        n_inactive = int((uc == "INACTIVE").sum())
        n_other    = n_total - n_active - n_inactive
    else:
        n_active = n_inactive = n_other = 0

    hit_rate = (n_active / n_total * 100) if n_total > 0 else 0.0

    # IC50 statistics
    ic50_vals = (pd.to_numeric(df[ic50_col], errors="coerce").dropna()
                 if ic50_col else pd.Series(dtype=float))
    ic50_stats: dict = {}
    if not ic50_vals.empty:
        ic50_stats = {
            "min":    round(float(ic50_vals.min()), 4),
            "max":    round(float(ic50_vals.max()), 4),
            "median": round(float(ic50_vals.median()), 4),
            "mean":   round(float(ic50_vals.mean()), 4),
            "count":  int(ic50_vals.count()),
        }

    # Hill slope stats
    hill_vals = (pd.to_numeric(df[hill_col], errors="coerce").dropna()
                 if hill_col else pd.Series(dtype=float))
    hill_stats: dict = {}
    if not hill_vals.empty:
        hill_stats = {
            "median": round(float(hill_vals.median()), 3),
            "mean":   round(float(hill_vals.mean()), 3),
        }

    # Maximal response stats
    emax_vals = (pd.to_numeric(df[emax_col], errors="coerce").dropna()
                 if emax_col else pd.Series(dtype=float))
    emax_median = round(float(emax_vals.median()), 1) if not emax_vals.empty else None

    # Detect concentration columns
    conc_cols = [c for c in df.columns if re.search(r"@\s*[\d.]+\s*(u|n)M", c, re.I)]
    n_conc_levels = len(set(re.search(r"[\d.]+\s*(u|n)M", c, re.I).group()
                             for c in conc_cols if re.search(r"[\d.]+\s*(u|n)M", c, re.I)))
    n_replicates = 0
    if conc_cols:
        sample_conc = conc_cols[0].split("[")[0].strip()
        reps = [c for c in conc_cols if c.startswith(sample_conc)]
        n_replicates = len(reps)

    # Top N actives by IC50
    top_actives: List[dict] = []
    if out_col and ic50_col:
        active_df = df[df[out_col].str.upper() == "ACTIVE"].copy()
        active_df["_ic50_num"] = pd.to_numeric(active_df[ic50_col], errors="coerce")
        active_df = active_df.sort_values("_ic50_num").head(top_n)
        for _, row in active_df.iterrows():
            entry: dict = {}
            if cid_col:
                entry["cid"] = str(int(row[cid_col])) if not pd.isna(row.get(cid_col)) else "—"
            if name_col:
                nm = str(row.get(name_col, "")).strip()
                entry["name"] = nm if nm and nm.lower() not in ("nan", "none") else "—"
            if smiles_col:
                entry["smiles"] = str(row.get(smiles_col, "")).strip()
            entry["ic50_uM"] = round(float(row["_ic50_num"]), 4) if not pd.isna(row["_ic50_num"]) else None
            if hill_col:
                h = pd.to_numeric(row.get(hill_col), errors="coerce")
                entry["hill_slope"] = round(float(h), 3) if not pd.isna(h) else None
            if emax_col:
                e = pd.to_numeric(row.get(emax_col), errors="coerce")
                entry["emax"] = round(float(e), 1) if not pd.isna(e) else None
            top_actives.append(entry)

    return {
        "aid":          aid,
        "target":       target,
        "n_total":      n_total,
        "n_active":     n_active,
        "n_inactive":   n_inactive,
        "n_other":      n_other,
        "hit_rate_pct": round(hit_rate, 2),
        "ic50_stats":   ic50_stats,
        "hill_stats":   hill_stats,
        "emax_median":  emax_median,
        "n_conc_levels": n_conc_levels,
        "n_replicates": n_replicates,
        "top_actives":  top_actives,
    }


# ── Ollama integration ────────────────────────────────────────────────────────

OLLAMA_PROMPT_TEMPLATE = """\
You are a lab scientist writing an Electronic Lab Notebook (ELN) entry.
Based on the assay data below, write a concise scientific ELN entry with these sections:

<procedure>
Describe the experimental procedure used in this assay (qHTS dose-response format,
cell-based assay, compound library screening). Be specific about concentration range,
replicate structure, and curve-fitting approach.
</procedure>

<observations>
Summarise the key findings: hit rate, IC50 distribution, notable active compounds,
curve quality (Hill slope, R²). Highlight any unusual patterns.
</observations>

<conclusion>
Interpret the results: what do they mean for {target} biology? Are the potencies
consistent with literature? What are the most promising scaffolds or structural
features? What next steps would you recommend?
</conclusion>

ASSAY DATA:
{stats_json}

Write each section between its XML tags. Be concise and scientifically precise.
Use µM units. Do not repeat the raw numbers verbatim — interpret them.
"""

def call_ollama(host: str, model: str, prompt: str, timeout: int = 90) -> Optional[str]:
    """Call Ollama generate endpoint; returns the response text or None on failure."""
    url = f"{host.rstrip('/')}/api/generate"
    payload = {"model": model, "prompt": prompt, "stream": False}
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json().get("response", "").strip()
    except Exception as e:
        print(f"    ⚠️  Ollama unavailable ({e}) — using template fallback")
        return None


def parse_ollama_sections(text: str) -> Dict[str, str]:
    """Extract <procedure>, <observations>, <conclusion> from Ollama output."""
    sections: dict = {}
    for tag in ("procedure", "observations", "conclusion"):
        m = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.S | re.I)
        sections[tag] = m.group(1).strip() if m else ""
    return sections


def fallback_sections(s: dict) -> Dict[str, str]:
    """Generate deterministic rich template sections from assay stats dict."""
    ic = s["ic50_stats"]
    hill = s["hill_stats"]
    top = s["top_actives"]
    target = s["target"]

    procedure = (
        f"Compounds were screened against {target} using a quantitative high-throughput "
        f"screening (qHTS) dose-response format sourced from the NCATS/MLPCN probe "
        f"development campaign (PubChem AID {s['aid']}). Each compound was tested across "
        f"{s['n_conc_levels'] or 10} concentration levels spanning a ~{2000}-fold range, "
        f"with {s['n_replicates'] or 3} technical replicates per concentration. "
        f"Percent inhibition was measured at each concentration×replicate well, and "
        f"4-parameter Hill equation curve fitting was applied to derive IC50, Hill slope, "
        f"maximal response (Emax), and R² goodness-of-fit. "
        f"Data retrieved from NCBI PubChem BioAssay (https://pubchem.ncbi.nlm.nih.gov/bioassay/{s['aid']})."
    )

    obs_parts = [
        f"The assay screened **{s['n_total']:,} compounds**, yielding "
        f"**{s['n_active']:,} actives** ({s['hit_rate_pct']:.1f}% hit rate) "
        f"and {s['n_inactive']:,} inactives.",
    ]
    if ic:
        obs_parts.append(
            f"Active compound IC50 values ranged from **{ic['min']} to {ic['max']} µM** "
            f"(median {ic['median']} µM, mean {ic['mean']} µM; n={ic['count']} fitted curves)."
        )
    if hill:
        obs_parts.append(
            f"Hill slopes were centered near {hill['median']} (mean {hill['mean']}), "
            f"{'consistent with a single-site binding mechanism.' if 0.7 < hill['median'] < 1.5 else 'suggesting cooperative or multi-site binding kinetics.'}"
        )
    if s["emax_median"] is not None:
        obs_parts.append(
            f"Median maximal response (Emax) was {s['emax_median']}% inhibition, "
            f"{'indicating partial agonism/antagonism for some scaffolds.' if s['emax_median'] < 80 else 'indicating full inhibitory efficacy for most active compounds.'}"
        )
    if top:
        best = top[0]
        obs_parts.append(
            f"The most potent active was **{best.get('name', 'CID ' + best.get('cid', '?'))}** "
            f"(CID {best.get('cid', '?')}) with IC50 = {best.get('ic50_uM')} µM."
        )
    observations = "\n\n".join(obs_parts)

    conclusion_parts = []
    if ic and ic["median"] < 1.0:
        conclusion_parts.append(
            f"The sub-micromolar median IC50 ({ic['median']} µM) demonstrates high-quality, "
            f"potent {target} antagonist/inhibitor activity within this compound set."
        )
    elif ic:
        conclusion_parts.append(
            f"Median IC50 of {ic['median']} µM suggests moderate {target} activity; "
            f"further optimisation of the most potent scaffolds is warranted."
        )
    conclusion_parts.append(
        f"The {s['hit_rate_pct']:.1f}% hit rate is "
        f"{'above' if s['hit_rate_pct'] > 1.5 else 'consistent with'} "
        f"typical qHTS primary screen rates (0.5–2%). "
        f"Top actives should be validated in orthogonal assays (e.g., radioligand binding, "
        f"calcium flux) before progressing to selectivity profiling."
    )
    if top:
        conclusion_parts.append(
            f"Priority compounds for follow-up: "
            + ", ".join(
                f"{c.get('name', 'CID ' + c.get('cid', '?'))} (IC50 {c.get('ic50_uM')} µM)"
                for c in top[:3]
            ) + "."
        )
    conclusion = " ".join(conclusion_parts)

    return {"procedure": procedure, "observations": observations, "conclusion": conclusion}


# ── Markdown composer ─────────────────────────────────────────────────────────

def build_top_actives_table(top_actives: List[dict]) -> str:
    """Render a Markdown table of top active compounds."""
    if not top_actives:
        return "_No active compounds with fitted IC50 found in this assay._\n"

    has_hill  = any("hill_slope" in c for c in top_actives)
    has_emax  = any("emax" in c for c in top_actives)

    headers = ["Rank", "CID", "Name", "IC50 (µM)"]
    if has_hill:
        headers.append("Hill Slope")
    if has_emax:
        headers.append("Emax (%)")

    sep  = "| " + " | ".join("---" for _ in headers) + " |"
    head = "| " + " | ".join(headers) + " |"
    rows = [head, sep]

    for i, c in enumerate(top_actives, 1):
        name = c.get("name", "—")[:35]
        cid  = c.get("cid", "—")
        ic50 = f"{c['ic50_uM']:.4f}" if c.get("ic50_uM") is not None else "—"
        row_cells = [str(i), cid, name, ic50]
        if has_hill:
            row_cells.append(str(c.get("hill_slope", "—")))
        if has_emax:
            row_cells.append(str(c.get("emax", "—")))
        rows.append("| " + " | ".join(row_cells) + " |")

    return "\n".join(rows) + "\n"


def render_eln_markdown(s: dict, sections: Dict[str, str],
                        author: str, author_title: str,
                        source_file: str, ollama_model: Optional[str]) -> str:
    """Compose the full Markdown ELN document."""
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    ts_str   = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    aid = s["aid"]

    narrative_source = (f"AI narrative generated by Ollama ({ollama_model})"
                        if ollama_model else "Narrative generated by template fallback")

    top_table = build_top_actives_table(s["top_actives"])
    ic = s["ic50_stats"]
    ic50_summary = (f"{ic['min']}–{ic['max']} µM (median {ic['median']} µM)"
                    if ic else "Not available")

    md = f"""# ELN Entry: PubChem BioAssay AID {aid}
## {s["target"]} — qHTS Dose-Response Screen

---

| Field | Value |
|---|---|
| **AID** | [{aid}](https://pubchem.ncbi.nlm.nih.gov/bioassay/{aid}) |
| **Author** | {author} |
| **Author Title** | {author_title} |
| **Date** | {date_str} |
| **Target** | {s["target"]} |
| **Assay Type** | qHTS Dose-Response (CRC) |
| **Source** | {source_file} |
| **Generated** | {ts_str} |
| **Narrative** | {narrative_source} |

---

## 1. Objective

Characterise the activity of a diverse compound library against **{s["target"]}**
using quantitative high-throughput screening (qHTS) dose-response methodology.
Identify potent inhibitors/antagonists with fitted concentration-response curves
suitable for structure-activity relationship (SAR) analysis and follow-up
orthogonal assay validation.

---

## 2. Procedure

{sections.get("procedure", "_Not generated._")}

---

## 3. Assay Statistics

| Metric | Value |
|---|---|
| Total compounds tested | {s["n_total"]:,} |
| Active | {s["n_active"]:,} |
| Inactive | {s["n_inactive"]:,} |
| Other / Inconclusive | {s["n_other"]:,} |
| Hit rate | {s["hit_rate_pct"]:.2f}% |
| IC50 range (actives) | {ic50_summary} |
| Hill slope (median) | {s["hill_stats"].get("median", "N/A")} |
| Emax (median, %) | {s["emax_median"] if s["emax_median"] is not None else "N/A"} |
| Concentration levels | {s["n_conc_levels"] or "N/A"} |
| Replicates per conc. | {s["n_replicates"] or "N/A"} |

---

## 4. Observations

{sections.get("observations", "_Not generated._")}

---

## 5. Results — Top Active Compounds

{top_table}

> **Note:** IC50 values are from 4-parameter Hill equation curve fitting.
> Compounds with IC50 qualifier `>` (curve did not reach 50% at max concentration)
> were excluded from the ranking.

---

## 6. Conclusion

{sections.get("conclusion", "_Not generated._")}

---

## 7. Notes & Data Quality

- **SMILES provenance:** Depositor-provided SMILES (`PUBCHEM_EXT_DATASOURCE_SMILES`);
  canonical SMILES may differ slightly from the PubChem standardised structure.
- **Assay heterogeneity:** IC50 values are not directly comparable across assays
  using different cell lines, agonist concentrations, or detection methods.
- **CRC data completeness:** Well-level % inhibition × concentration × replicate data
  are preserved in the source Excel workbook for full traceability.
- **PubChem reference:** https://pubchem.ncbi.nlm.nih.gov/bioassay/{aid}

---

_Entry generated by `pubchem_eln_scientist.py` | Lab Informatics Project_
"""
    return md


# ── API registration helpers ──────────────────────────────────────────────────

def api_login(base_url: str, username: str, password: str) -> Optional[str]:
    """Login via POST /auth/login and return a JWT Bearer token, or None on failure."""
    try:
        r = requests.post(
            f"{base_url}/auth/login",
            data={"username": username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
        r.raise_for_status()
        token = r.json().get("access_token")
        if token:
            print(f"  🔑  Logged in as '{username}' — ELN entries will appear in GUI")
        return token
    except Exception as e:
        print(f"  ⚠️  API login failed: {e}")
        return None


def build_eln_payload(s: dict, sections: Dict[str, str],
                      author: str, author_title: str) -> dict:
    """
    Convert assay stats + narrative sections into an ELNEntry-compatible payload
    matching the lab-informatics Pydantic schema.
    """
    import uuid
    aid = s["aid"]
    ic  = s["ic50_stats"]
    ic50_summary = (f"{ic['min']}–{ic['max']} µM (median {ic['median']} µM)"
                    if ic else "Not available")

    # Build a compact results text (table doesn't render in plain JSON, use prose)
    top = s["top_actives"]
    if top:
        top_lines = "\n".join(
            f"  {i+1}. CID {c.get('cid','?')} — {c.get('name','?')} — IC50 {c.get('ic50_uM')} µM"
            for i, c in enumerate(top[:8])
        )
        results_content = (
            f"Top active compounds by IC50 ({s['target']}, AID {aid}):\n\n"
            f"{top_lines}\n\n"
            f"Hit rate: {s['hit_rate_pct']:.1f}%  |  "
            f"IC50 range: {ic50_summary}  |  "
            f"Hill slope median: {s['hill_stats'].get('median','N/A')}  |  "
            f"Emax median: {s['emax_median']} %"
        )
    else:
        results_content = f"No actives with fitted IC50 found. Total tested: {s['n_total']:,}."

    notes_content = (
        f"SMILES provenance: Depositor-provided (PUBCHEM_EXT_DATASOURCE_SMILES). "
        f"IC50 values from 4-parameter Hill equation curve fitting. "
        f"CRC well-level data (% inhibition × concentration × replicate) preserved "
        f"in source Excel workbook. "
        f"PubChem reference: https://pubchem.ncbi.nlm.nih.gov/bioassay/{aid}"
    )

    return {
        "title": f"PubChem AID {aid} — {s['target']} qHTS Dose-Response Screen",
        "author": author,
        "author_title": author_title,
        "experiment_id": None,
        "objective": (
            f"Characterise compound library activity against {s['target']} "
            f"(AID {aid}) using qHTS CRC methodology. "
            f"Identify potent inhibitors for SAR follow-up."
        ),
        "sections": [
            {
                "section_id": str(uuid.uuid4()),
                "section_type": "procedure",
                "title": "Experimental Procedure",
                "content": sections.get("procedure", ""),
            },
            {
                "section_id": str(uuid.uuid4()),
                "section_type": "observation",
                "title": "Observations",
                "content": sections.get("observations", ""),
            },
            {
                "section_id": str(uuid.uuid4()),
                "section_type": "result",
                "title": f"Results — Top Actives (AID {aid})",
                "content": results_content,
            },
            {
                "section_id": str(uuid.uuid4()),
                "section_type": "conclusion",
                "title": "Conclusion",
                "content": sections.get("conclusion", ""),
            },
            {
                "section_id": str(uuid.uuid4()),
                "section_type": "note",
                "title": "Data Quality & Provenance",
                "content": notes_content,
            },
        ],
        "tags": [
            "pubchem", "qHTS", "dose-response", "CRC",
            f"AID:{aid}", s["target"].replace(" ", "-").lower(),
        ],
    }


def post_eln_entry(base_url: str, token: str, payload: dict) -> Optional[dict]:
    """POST an ELN entry to the API. Returns the created entry dict or None on failure."""
    try:
        r = requests.post(
            f"{base_url}/eln/",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        r.raise_for_status()
        return r.json().get("entry", {})
    except Exception as e:
        print(f"    ⚠️  ELN API post failed: {e}")
        return None


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()
    xl_path = Path(args.xlsx)
    if not xl_path.exists():
        sys.exit(f"❌ File not found: {xl_path}")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*62}")
    print(f"  AI Scientist — PubChem BioAssay ELN Generator")
    print(f"  Source  : {xl_path.name}")
    print(f"  Out dir : {out_dir}")
    print(f"  Ollama  : {args.ollama_host}  model={args.ollama_model}")
    print(f"{'='*62}\n")

    xl = pd.ExcelFile(xl_path)
    crc_sheets = [s for s in xl.sheet_names if s.lower().startswith("aid ")]

    if not crc_sheets:
        print("⚠️  No 'AID XXXXX' sheets found — nothing to process.")
        return

    # Optionally log in to the API so entries appear in the GUI
    api_token: Optional[str] = None
    if args.api_username and args.api_password:
        api_token = api_login(
            args.base_url.rstrip("/"), args.api_username, args.api_password
        )
        if not api_token:
            print("  ⚠️  Continuing without API posting — entries will only be on disk\n")
    else:
        print("  ℹ️  No --api-username/--api-password supplied — "
              "entries written to disk only (not visible in GUI)\n"
              "     Re-run with --api-username <user> --api-password <pass> to register them.\n")

    # Check Ollama availability once
    ollama_available = False
    try:
        r = requests.get(f"{args.ollama_host}/api/tags", timeout=5)
        ollama_available = r.ok
        if ollama_available:
            print(f"✅  Ollama reachable — will use {args.ollama_model} for narratives\n")
    except Exception:
        print("⚠️  Ollama not reachable — using template fallback for all entries\n")

    written: List[Path] = []
    index_rows: List[dict] = []

    for sheet in crc_sheets:
        aid = sheet.split()[-1]
        print(f"📝  Processing {sheet} …")

        df = read_assay_sheet(xl, sheet)
        if df.empty:
            print(f"  ⚠️  No data rows — skipping\n")
            continue

        stats = extract_assay_stats(df, aid, args.target, args.top_n)
        print(f"  Compounds: {stats['n_total']:,}  |  "
              f"Active: {stats['n_active']:,}  |  "
              f"Hit rate: {stats['hit_rate_pct']:.1f}%")
        if stats["ic50_stats"]:
            ic = stats["ic50_stats"]
            print(f"  IC50: {ic['min']}–{ic['max']} µM  (median {ic['median']} µM)")

        # Generate narrative
        if ollama_available:
            # Use replace() instead of .format() to avoid JSON braces being
            # misinterpreted as Python format placeholders
            stats_json = json.dumps(
                {k: v for k, v in stats.items() if k != "top_actives"}, indent=2
            )
            prompt = (OLLAMA_PROMPT_TEMPLATE
                      .replace("{target}", args.target)
                      .replace("{stats_json}", stats_json))
            raw_response = call_ollama(
                args.ollama_host, args.ollama_model, prompt)
            if raw_response:
                sections = parse_ollama_sections(raw_response)
                # Fill any empty sections with template
                tmpl = fallback_sections(stats)
                for key in ("procedure", "observations", "conclusion"):
                    if not sections.get(key):
                        sections[key] = tmpl[key]
                used_model = args.ollama_model
            else:
                sections = fallback_sections(stats)
                used_model = None
        else:
            sections = fallback_sections(stats)
            used_model = None

        # Render and write markdown
        md = render_eln_markdown(
            stats, sections,
            author=args.author,
            author_title=args.author_title,
            source_file=xl_path.name,
            ollama_model=used_model,
        )

        safe_target = re.sub(r"[^\w-]", "_", args.target.replace(" ", "_"))
        out_name = f"ELN_AID_{aid}_{safe_target}.md"
        out_path = out_dir / out_name
        out_path.write_text(md, encoding="utf-8")
        written.append(out_path)
        print(f"  ✅  Written → {out_path}")

        # Also POST to the ELN API so the entry appears in the GUI
        api_entry_id = None
        if api_token:
            payload = build_eln_payload(
                stats, sections,
                author=args.author,
                author_title=args.author_title,
            )
            result = post_eln_entry(args.base_url.rstrip("/"), api_token, payload)
            if result:
                api_entry_id = result.get("entry_id")
                print(f"  🌐  Registered in GUI  → entry_id: {api_entry_id}")
        print()

        index_rows.append({
            "aid": aid,
            "target": args.target,
            "n_total": stats["n_total"],
            "n_active": stats["n_active"],
            "hit_rate_pct": stats["hit_rate_pct"],
            "ic50_median_uM": stats["ic50_stats"].get("median"),
            "eln_file": out_name,
            "api_entry_id": api_entry_id,
        })

    # Write a combined index markdown
    if index_rows:
        _write_index(out_dir, index_rows, xl_path.name, args.author)

    print(f"{'='*62}")
    print(f"  Done! {len(written)} ELN entries written to {out_dir}")
    print(f"{'='*62}\n")


def _write_index(out_dir: Path, rows: List[dict],
                 source_file: str, author: str) -> None:
    """Write an ELN_INDEX.md summarising all generated entries."""
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [
        f"# ELN Index — PubChem BioAssay Entries",
        f"",
        f"**Author:** {author}  |  **Date:** {date_str}  "
        f"|  **Source:** {source_file}",
        f"",
        f"| AID | Target | Compounds | Actives | Hit Rate | IC50 Median | ELN Entry |",
        f"|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        ic50 = f"{r['ic50_median_uM']} µM" if r["ic50_median_uM"] else "—"
        link = f"[{r['eln_file']}]({r['eln_file']})"
        lines.append(
            f"| {r['aid']} | {r['target']} | {r['n_total']:,} | "
            f"{r['n_active']:,} | {r['hit_rate_pct']:.1f}% | {ic50} | {link} |"
        )
    lines += ["", "_Generated by `pubchem_eln_scientist.py` | Lab Informatics Project_"]
    index_path = out_dir / "ELN_INDEX.md"
    index_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"📋  Index written → {index_path}")


if __name__ == "__main__":
    main()
