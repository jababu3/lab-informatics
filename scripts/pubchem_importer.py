#!/usr/bin/env python3
"""
pubchem_importer.py
───────────────────
Reads a PubChem BioAssay Excel workbook (produced by the pubchem-bioassay skill)
and imports it into the lab-informatics project:

  1. Registers every unique compound   → POST /compounds/
  2. Creates an Experiment record      → POST /experiments/
     for each CRC assay sheet and each IC50 summary sheet
  3. Writes an import manifest JSON   → <out-dir>/import_manifest_<ts>.json

Usage:
    cd /path/to/lab-informatics/backend
    python ../scripts/pubchem_importer.py \\
        --xlsx ../data/Orexin_PubChem_BioAssay.xlsx \\
        --base-url http://localhost:8000 \\
        --out-dir ../reports/ \\
        [--dry-run]

Dependencies: requests, pandas, openpyxl
Install:  pip install requests pandas openpyxl
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import requests

# ── CLI args ──────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description="Import PubChem BioAssay data into lab-informatics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--xlsx", required=True,
                   help="Path to PubChem BioAssay Excel workbook")
    p.add_argument("--base-url", default="http://localhost:8000",
                   help="Lab-informatics API base URL (default: http://localhost:8000)")
    p.add_argument("--out-dir", default="reports",
                   help="Directory to write the import manifest JSON")
    p.add_argument("--dry-run", action="store_true",
                   help="Parse only; do not POST to API")
    p.add_argument("--delay", type=float, default=0.05,
                   help="Seconds between API calls (default: 0.05)")
    return p.parse_args()


# ── API helpers ───────────────────────────────────────────────────────────────

def post_compound(base_url: str, name: str, smiles: str,
                  tags: List[str], delay: float) -> Optional[dict]:
    payload = {"name": name, "smiles": smiles, "tags": tags}
    try:
        r = requests.post(f"{base_url}/compounds/", json=payload, timeout=15)
        r.raise_for_status()
        time.sleep(delay)
        return r.json().get("compound", {})
    except Exception as e:
        print(f"    ⚠️  Compound '{name}': {e}")
        return None


def post_experiment(base_url: str, title: str, description: str,
                    compound_ids: List[str], assay_type: str,
                    target: str, delay: float) -> Optional[dict]:
    payload = {
        "title": title,
        "description": description,
        "compound_ids": compound_ids,
        "assay_type": assay_type,
        "target": target,
        "status": "completed",
    }
    try:
        r = requests.post(f"{base_url}/experiments/", json=payload, timeout=15)
        r.raise_for_status()
        time.sleep(delay)
        return r.json().get("experiment", {})
    except Exception as e:
        print(f"    ⚠️  Experiment '{title[:50]}': {e}")
        return None


# ── Excel readers ─────────────────────────────────────────────────────────────

def _find_header_row(raw: pd.DataFrame, markers: List[str]) -> Optional[int]:
    """Return the 0-based row index whose cells contain any of the marker strings."""
    for i, row in raw.iterrows():
        vals = [str(v).strip().upper() for v in row if not pd.isna(v)]
        if any(m.upper() in vals for m in markers):
            return i
    return None


def read_all_compounds(xl: pd.ExcelFile) -> pd.DataFrame:
    """Read the 'All Compounds' deduplicated sheet.

    The sheet has a title banner in row 0; real column headers are in row 1.
    We detect this by finding the row whose values include 'CID' and 'SMILES'.
    """
    if "All Compounds" not in xl.sheet_names:
        print("  ⚠️  'All Compounds' sheet not found.")
        return pd.DataFrame()
    raw = xl.parse("All Compounds", header=None)
    # Find the real header row
    header_row = 0
    for i, row in raw.iterrows():
        vals = [str(v).strip().upper() for v in row if not pd.isna(v)]
        if "CID" in vals and ("SMILES" in vals or "NAME" in vals):
            header_row = i
            break
    df = xl.parse("All Compounds", header=header_row)
    df.columns = [str(c).strip() for c in df.columns]
    # Drop rows where CID is not numeric (sub-headers, blank rows)
    cid_col = _col(df, "CID")
    if cid_col:
        df = df[pd.to_numeric(df[cid_col], errors="coerce").notna()].reset_index(drop=True)
    return df


def read_assay_sheet(xl: pd.ExcelFile, sheet_name: str) -> pd.DataFrame:
    """
    Read a CRC assay sheet (named 'AID XXXXX').
    Skips the 6-row metadata header by locating the real column-header row.
    """
    raw = xl.parse(sheet_name, header=None)
    header_row = _find_header_row(raw, ["PUBCHEM_RESULT_TAG", "PUBCHEM_CID"])
    if header_row is None:
        return pd.DataFrame()
    df = xl.parse(sheet_name, header=header_row)
    df.columns = [str(c).strip() for c in df.columns]
    # Keep only real data rows (PUBCHEM_RESULT_TAG is numeric)
    if "PUBCHEM_RESULT_TAG" in df.columns:
        df = df[pd.to_numeric(df["PUBCHEM_RESULT_TAG"],
                              errors="coerce").notna()].reset_index(drop=True)
    return df


def _col(df: pd.DataFrame, *candidates: str) -> Optional[str]:
    """Return first column name that matches any candidate substring (case-insensitive)."""
    for c in df.columns:
        for cand in candidates:
            if cand.upper() in c.upper():
                return c
    return None


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()
    xl_path = Path(args.xlsx)
    if not xl_path.exists():
        sys.exit(f"❌ File not found: {xl_path}")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    base_url = args.base_url.rstrip("/")
    dry = args.dry_run

    print(f"\n{'='*62}")
    print(f"  PubChem BioAssay → Lab Informatics Importer")
    print(f"  Source : {xl_path.name}")
    print(f"  API    : {base_url}  {'(DRY RUN)' if dry else ''}")
    print(f"{'='*62}\n")

    xl = pd.ExcelFile(xl_path)

    manifest: dict = {
        "import_timestamp": datetime.now(timezone.utc).isoformat(),
        "source_file": str(xl_path.resolve()),
        "api_base_url": base_url,
        "dry_run": dry,
        "compounds": [],
        "experiments": [],
        "errors": [],
    }

    # ── Step 1: Import compounds ──────────────────────────────────────────────
    print("📦  Step 1 — Importing compounds from 'All Compounds' sheet …")
    comp_df = read_all_compounds(xl)
    cid_to_api_id: Dict[str, str] = {}

    if comp_df.empty:
        print("  (No compound data found)\n")
    else:
        cid_col    = _col(comp_df, "CID")
        name_col   = _col(comp_df, "PREFERRED", "NAME")
        smiles_col = _col(comp_df, "SMILES")
        act_col    = _col(comp_df, "ACTIVITY")

        if not smiles_col:
            print("  ⚠️  No SMILES column — skipping compound import\n")
        else:
            ok = 0
            for _, row in comp_df.iterrows():
                smiles = str(row.get(smiles_col, "")).strip()
                if not smiles or smiles.lower() in ("nan", "none", ""):
                    continue

                cid = (str(int(row[cid_col])) if cid_col
                       and not pd.isna(row.get(cid_col)) else "unknown")
                raw_name = str(row.get(name_col, "")).strip() if name_col else ""
                name = raw_name if raw_name and raw_name.lower() not in ("nan", "none") \
                    else f"PubChem CID {cid}"

                tags = ["pubchem", f"cid:{cid}"]
                if act_col and not pd.isna(row.get(act_col)):
                    tags.append(f"activity:{str(row[act_col]).lower()}")

                print(f"  ↑ {name[:45]:<45} CID {cid}")
                if not dry:
                    res = post_compound(base_url, name, smiles, tags, args.delay)
                    if res:
                        api_id = res.get("_id", "")
                        cid_to_api_id[cid] = api_id
                        manifest["compounds"].append(
                            {"cid": cid, "name": name, "api_id": api_id})
                        ok += 1
                    else:
                        manifest["errors"].append(
                            {"type": "compound", "cid": cid, "name": name})
                else:
                    manifest["compounds"].append(
                        {"cid": cid, "name": name, "dry_run": True})
                    ok += 1

            total = len([r for _, r in comp_df.iterrows()
                         if str(r.get(smiles_col, "")).strip()
                         not in ("", "nan", "none")])
            print(f"\n  ✅  Registered {ok}/{total} compounds\n")

    # ── Step 2: CRC assay sheets → Experiments ───────────────────────────────
    print("🧪  Step 2 — Creating Experiment records for CRC assay sheets …")
    crc_sheets = [s for s in xl.sheet_names if s.lower().startswith("aid ")]

    for sheet in crc_sheets:
        aid = sheet.split()[-1]
        print(f"\n  {sheet}")
        df = read_assay_sheet(xl, sheet)
        if df.empty:
            print("    ⚠️  No data rows — skipping")
            continue

        cid_col_a  = _col(df, "PUBCHEM_CID")
        out_col    = _col(df, "OUTCOME")
        ic50_col   = _col(df, "IC50")
        name_col_a = _col(df, "COMPOUND_NAME", "NAME")

        # Gather API IDs for compounds in this assay
        assay_cids = (
            [str(int(v)) for v in df[cid_col_a].dropna()
             if str(v).strip() not in ("nan", "")]
            if cid_col_a else []
        )
        api_ids = [cid_to_api_id[c] for c in assay_cids if c in cid_to_api_id]

        n_total  = len(df)
        n_active = (int((df[out_col].str.upper() == "ACTIVE").sum())
                    if out_col else "?")

        # IC50 summary stats
        ic50_summary = ""
        if ic50_col:
            ic50_vals = pd.to_numeric(df[ic50_col], errors="coerce").dropna()
            if not ic50_vals.empty:
                ic50_summary = (
                    f"IC50 range {ic50_vals.min():.3f}–{ic50_vals.max():.3f} µM "
                    f"(median {ic50_vals.median():.3f} µM). "
                )

        title = f"PubChem AID {aid} — qHTS Dose-Response Bioassay"
        description = (
            f"PubChem BioAssay AID {aid} — full CRC (concentration-response curve) "
            f"well-level data. {n_total} compounds tested, {n_active} actives. "
            f"{ic50_summary}"
            f"Source: {xl_path.name}. "
            f"Data format: 10 concentrations × 3 replicates % inhibition + "
            f"fitted curve parameters (IC50, Hill slope, R², Maximal Response)."
        )

        print(f"    Compounds: {n_total} total, {n_active} active  |  "
              f"API IDs linked: {len(api_ids)}")

        if not dry:
            res = post_experiment(
                base_url, title, description, api_ids,
                assay_type="qHTS_dose_response",
                target="Orexin Receptor (HCRTR1/HCRTR2)",
                delay=args.delay,
            )
            exp_id = res.get("_id", "") if res else None
            manifest["experiments"].append({
                "aid": aid, "sheet": sheet, "title": title,
                "n_compounds": n_total, "n_active": n_active,
                "api_id": exp_id, "compound_api_ids_linked": len(api_ids),
            })
        else:
            manifest["experiments"].append({
                "aid": aid, "sheet": sheet, "title": title,
                "n_compounds": n_total, "n_active": n_active, "dry_run": True,
            })
        print(f"    ✅  Experiment record created for AID {aid}")

    # ── Step 3: IC50 summary sheets ───────────────────────────────────────────
    print("\n📋  Step 3 — IC50 summary sheets …")
    ic50_sheets = [s for s in xl.sheet_names
                   if "ic50" in s.lower() and s not in crc_sheets]

    for sheet in ic50_sheets:
        print(f"\n  {sheet}")
        try:
            df = xl.parse(sheet)
            df.columns = [str(c).strip() for c in df.columns]
        except Exception:
            continue
        if len(df) < 2:
            continue

        n = len(df)
        title = f"PubChem IC50 Summary — {sheet}"
        description = (
            f"Single-concentration IC50 summary data from PubChem, "
            f"sheet '{sheet}'. {n} compound records. "
            f"Source: {xl_path.name}."
        )
        print(f"    {n} records")
        if not dry:
            res = post_experiment(
                base_url, title, description, [],
                assay_type="IC50_summary",
                target="Orexin Receptor (HCRTR2)",
                delay=args.delay,
            )
            exp_id = res.get("_id", "") if res else None
            manifest["experiments"].append(
                {"sheet": sheet, "title": title, "n_records": n, "api_id": exp_id})
        else:
            manifest["experiments"].append(
                {"sheet": sheet, "title": title, "n_records": n, "dry_run": True})
        print(f"    ✅  Experiment record created for {sheet}")

    # ── Write manifest ────────────────────────────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    manifest_path = out_dir / f"import_manifest_{ts}.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, default=str)

    print(f"\n{'='*62}")
    print(f"  Import complete!")
    print(f"  Compounds   : {len(manifest['compounds'])}")
    print(f"  Experiments : {len(manifest['experiments'])}")
    print(f"  Errors      : {len(manifest['errors'])}")
    print(f"  Manifest    : {manifest_path}")
    print(f"{'='*62}\n")

    return str(manifest_path)


if __name__ == "__main__":
    main()
