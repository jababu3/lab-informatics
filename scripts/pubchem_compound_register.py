#!/usr/bin/env python3
"""
pubchem_compound_register.py
─────────────────────────────
Registers compounds from a PubChem BioAssay Excel workbook into the
lab-informatics project via POST /compounds/.

Reads compound data from TWO sources per workbook:
  1. 'All Compounds' sheet  — canonical SMILES, preferred names, MW, XLogP, TPSA
  2. Each 'AID XXXXX' sheet — per-assay activity outcome + fitted IC50, Hill slope, Emax

Compounds are merged by CID and registered with rich tags:
  ["pubchem", "cid:12345", "orexin", "active:624410", "inactive:624409",
   "ic50_624410:0.2774uM", "hcrtr1"]

Does NOT require authentication (POST /compounds/ is open).
Writes a JSON manifest of all registered compound API IDs for downstream use.

Usage:
    cd lab-informatics/backend
    python ../scripts/pubchem_compound_register.py \\
        --xlsx ~/Orexin_PubChem_BioAssay.xlsx \\
        --base-url http://localhost:8000 \\
        --out-dir ../reports/ \\
        [--dry-run]

Dependencies: requests, pandas, openpyxl
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import requests

# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description="Register PubChem BioAssay compounds into lab-informatics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--xlsx", required=True,
                   help="PubChem BioAssay Excel workbook")
    p.add_argument("--base-url", default="http://localhost:8000",
                   help="API base URL (default: http://localhost:8000)")
    p.add_argument("--out-dir", default="reports",
                   help="Directory for the JSON manifest (default: reports/)")
    p.add_argument("--dry-run", action="store_true",
                   help="Parse and preview only — no API calls")
    p.add_argument("--delay", type=float, default=0.05,
                   help="Seconds between API calls (default: 0.05)")
    p.add_argument("--target-tags", nargs="+", default=["orexin", "hcrtr1"],
                   help="Extra target tags to apply to every compound "
                        "(default: orexin hcrtr1)")
    return p.parse_args()


# ── Column finder ─────────────────────────────────────────────────────────────

def _col(df: pd.DataFrame, *candidates: str) -> Optional[str]:
    for c in df.columns:
        for cand in candidates:
            if cand.upper() in c.upper():
                return c
    return None


# ── Source 1: 'All Compounds' sheet ──────────────────────────────────────────

def read_all_compounds_sheet(xl: pd.ExcelFile) -> Dict[str, dict]:
    """
    Parse the 'All Compounds' summary sheet.
    Returns a dict keyed by CID string → compound property dict.
    The sheet has a title banner in row 0; real headers are in row 1.
    """
    if "All Compounds" not in xl.sheet_names:
        print("  ⚠️  'All Compounds' sheet not found — skipping summary data")
        return {}

    raw = xl.parse("All Compounds", header=None)
    # Find real header row (contains both CID and SMILES)
    header_row = 0
    for i, row in raw.iterrows():
        vals = [str(v).strip().upper() for v in row if not pd.isna(v)]
        if "CID" in vals and ("SMILES" in vals or "NAME" in vals):
            header_row = i
            break

    df = xl.parse("All Compounds", header=header_row)
    df.columns = [str(c).strip() for c in df.columns]

    cid_col    = _col(df, "CID")
    name_col   = _col(df, "PREFERRED", "NAME")
    smiles_col = _col(df, "SMILES")
    mw_col     = _col(df, "MW")
    xlogp_col  = _col(df, "XLOGP", "LOGP")
    tpsa_col   = _col(df, "TPSA")
    hbd_col    = _col(df, "HBD")
    hba_col    = _col(df, "HBA")
    act_col    = _col(df, "ACTIVITY")

    # Keep only rows where CID is numeric
    if cid_col:
        df = df[pd.to_numeric(df[cid_col], errors="coerce").notna()].reset_index(drop=True)

    compounds: Dict[str, dict] = {}
    for _, row in df.iterrows():
        cid = str(int(row[cid_col])) if cid_col and not pd.isna(row.get(cid_col)) else None
        if not cid:
            continue

        smiles = str(row.get(smiles_col, "")).strip() if smiles_col else ""
        if smiles.lower() in ("nan", "none", ""):
            smiles = ""

        raw_name = str(row.get(name_col, "")).strip() if name_col else ""
        name = raw_name if raw_name and raw_name.lower() not in ("nan", "none") \
            else f"PubChem CID {cid}"

        props: dict = {"cid": cid, "name": name, "smiles": smiles}

        for col, key in [(mw_col, "mw"), (xlogp_col, "xlogp"),
                         (tpsa_col, "tpsa"), (hbd_col, "hbd"), (hba_col, "hba")]:
            if col:
                v = pd.to_numeric(row.get(col), errors="coerce")
                if not pd.isna(v):
                    props[key] = round(float(v), 3)

        if act_col and not pd.isna(row.get(act_col)):
            props["overall_activity"] = str(row[act_col]).strip().lower()

        compounds[cid] = props

    print(f"  📋  'All Compounds' sheet: {len(compounds)} compounds with SMILES/name data")
    return compounds


# ── Source 2: Individual AID assay sheets ────────────────────────────────────

def read_assay_sheet(xl: pd.ExcelFile, sheet_name: str) -> Dict[str, dict]:
    """
    Parse one CRC assay sheet (named 'AID XXXXX').
    Returns a dict keyed by CID → per-assay activity record.
    Handles the 6-row metadata header by finding the real column-header row.
    """
    raw = xl.parse(sheet_name, header=None)
    header_row = None
    for i, row in raw.iterrows():
        vals = [str(v).strip().upper() for v in row if not pd.isna(v)]
        if "PUBCHEM_RESULT_TAG" in vals or "PUBCHEM_CID" in vals:
            header_row = i
            break
    if header_row is None:
        return {}

    df = xl.parse(sheet_name, header=header_row)
    df.columns = [str(c).strip() for c in df.columns]

    # Drop metadata rows (non-numeric PUBCHEM_RESULT_TAG)
    if "PUBCHEM_RESULT_TAG" in df.columns:
        df = df[pd.to_numeric(df["PUBCHEM_RESULT_TAG"],
                              errors="coerce").notna()].reset_index(drop=True)

    cid_col    = _col(df, "PUBCHEM_CID")
    out_col    = _col(df, "OUTCOME")
    ic50_col   = _col(df, "IC50")
    hill_col   = _col(df, "HILL", "SLOPE")
    emax_col   = _col(df, "MAXIMAL", "EMAX")
    smiles_col = _col(df, "SMILES")
    name_col   = _col(df, "COMPOUND_NAME", "NAME")

    aid = sheet_name.split()[-1]
    records: Dict[str, dict] = {}

    for _, row in df.iterrows():
        cid = str(int(row[cid_col])) if cid_col and not pd.isna(row.get(cid_col)) else None
        if not cid:
            continue

        rec: dict = {"cid": cid, "aid": aid}

        if out_col:
            rec["outcome"] = str(row[out_col]).strip().lower()

        if ic50_col:
            v = pd.to_numeric(row.get(ic50_col), errors="coerce")
            if not pd.isna(v):
                rec["ic50_uM"] = round(float(v), 4)

        if hill_col:
            v = pd.to_numeric(row.get(hill_col), errors="coerce")
            if not pd.isna(v):
                rec["hill_slope"] = round(float(v), 3)

        if emax_col:
            v = pd.to_numeric(row.get(emax_col), errors="coerce")
            if not pd.isna(v):
                rec["emax_pct"] = round(float(v), 1)

        # Grab SMILES from assay sheet if not in All Compounds
        if smiles_col:
            s = str(row.get(smiles_col, "")).strip()
            if s and s.lower() not in ("nan", "none", ""):
                rec["smiles"] = s

        if name_col:
            n = str(row.get(name_col, "")).strip()
            if n and n.lower() not in ("nan", "none", ""):
                rec["name"] = n

        records[cid] = rec

    return records


# ── Merge + tag builder ───────────────────────────────────────────────────────

def merge_compounds(
    summary: Dict[str, dict],
    assay_data: Dict[str, Dict[str, dict]],   # {aid: {cid: record}}
    target_tags: List[str],
) -> List[dict]:
    """
    Merge summary sheet + per-assay records into a flat list of compounds
    ready for API registration. Each compound gets:
      - name, smiles from summary (or assay sheet as fallback)
      - tags: pubchem, cid:X, target tags, active/inactive per AID, ic50 per AID
      - physicochemical props (MW, XLogP, TPSA, HBD, HBA) if available
    """
    # Collect all CIDs seen across summary + all assay sheets
    all_cids = set(summary.keys())
    for aid_records in assay_data.values():
        all_cids.update(aid_records.keys())

    merged: List[dict] = []

    for cid in sorted(all_cids, key=lambda x: int(x) if x.isdigit() else 0):
        base = summary.get(cid, {})
        smiles = base.get("smiles", "")
        name   = base.get("name", f"PubChem CID {cid}")

        # Fall back to any assay sheet that has SMILES for this CID
        if not smiles:
            for aid_records in assay_data.values():
                rec = aid_records.get(cid, {})
                if rec.get("smiles"):
                    smiles = rec["smiles"]
                    break

        # Fall back to any assay sheet that has a name
        if name == f"PubChem CID {cid}":
            for aid_records in assay_data.values():
                rec = aid_records.get(cid, {})
                if rec.get("name"):
                    name = rec["name"]
                    break

        # Skip compounds with no SMILES at all
        if not smiles:
            continue

        # Build tags
        tags = ["pubchem", f"cid:{cid}"] + list(target_tags)

        # Add physicochemical property tags from summary
        for key, label in [("mw", "mw"), ("xlogp", "logp"),
                            ("tpsa", "tpsa"), ("overall_activity", "activity")]:
            val = base.get(key)
            if val is not None:
                tags.append(f"{label}:{val}")

        # Add per-assay activity tags
        assay_summaries = []
        for aid, aid_records in sorted(assay_data.items()):
            rec = aid_records.get(cid)
            if not rec:
                continue
            outcome = rec.get("outcome", "")
            if outcome in ("active", "inactive"):
                tags.append(f"{outcome}:{aid}")
            if rec.get("ic50_uM") is not None:
                tags.append(f"ic50_{aid}:{rec['ic50_uM']}uM")
            assay_summaries.append({
                "aid":        aid,
                "outcome":    outcome,
                "ic50_uM":    rec.get("ic50_uM"),
                "hill_slope": rec.get("hill_slope"),
                "emax_pct":   rec.get("emax_pct"),
            })

        merged.append({
            "cid":             cid,
            "name":            name,
            "smiles":          smiles,
            "tags":            tags,
            "mw":              base.get("mw"),
            "xlogp":           base.get("xlogp"),
            "tpsa":            base.get("tpsa"),
            "hbd":             base.get("hbd"),
            "hba":             base.get("hba"),
            "assay_summaries": assay_summaries,
        })

    return merged


# ── API call ──────────────────────────────────────────────────────────────────

def post_compound(base_url: str, name: str, smiles: str,
                  tags: List[str], delay: float) -> Optional[dict]:
    try:
        r = requests.post(
            f"{base_url}/compounds/",
            json={"name": name, "smiles": smiles, "tags": tags},
            timeout=15,
        )
        r.raise_for_status()
        time.sleep(delay)
        return r.json().get("compound", {})
    except Exception as e:
        print(f"    ⚠️  '{name}': {e}")
        return None


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()
    xl_path = Path(args.xlsx)
    if not xl_path.exists():
        sys.exit(f"❌  File not found: {xl_path}")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    base_url = args.base_url.rstrip("/")
    dry = args.dry_run

    print(f"\n{'='*62}")
    print(f"  PubChem Compound Registrar")
    print(f"  Source  : {xl_path.name}")
    print(f"  API     : {base_url}  {'(DRY RUN)' if dry else ''}")
    print(f"  Tags    : {args.target_tags}")
    print(f"{'='*62}\n")

    xl = pd.ExcelFile(xl_path)

    # ── Step 1: Read 'All Compounds' summary ─────────────────────────────────
    print("📋  Step 1 — Reading 'All Compounds' summary sheet …")
    summary = read_all_compounds_sheet(xl)

    # ── Step 2: Read each AID sheet ──────────────────────────────────────────
    crc_sheets = [s for s in xl.sheet_names if s.lower().startswith("aid ")]
    assay_data: Dict[str, Dict[str, dict]] = {}

    print(f"\n🧪  Step 2 — Reading {len(crc_sheets)} CRC assay sheet(s) …")
    for sheet in crc_sheets:
        aid = sheet.split()[-1]
        records = read_assay_sheet(xl, sheet)
        assay_data[aid] = records
        actives = sum(1 for r in records.values() if r.get("outcome") == "active")
        print(f"  AID {aid}: {len(records)} compounds, {actives} active")

    # ── Step 3: Merge ─────────────────────────────────────────────────────────
    print(f"\n🔀  Step 3 — Merging …")
    compounds = merge_compounds(summary, assay_data, args.target_tags)
    print(f"  {len(compounds)} unique compounds with SMILES ready for registration")

    # Activity breakdown
    active_in_any = sum(
        1 for c in compounds
        if any(s.get("outcome") == "active" for s in c.get("assay_summaries", []))
    )
    print(f"  {active_in_any} active in at least one assay")
    print(f"  {len(compounds) - active_in_any} inactive / not tested\n")

    # Preview top 5
    if dry:
        print("  Sample (first 5):")
        for c in compounds[:5]:
            active_aids = [s["aid"] for s in c["assay_summaries"]
                           if s.get("outcome") == "active"]
            best_ic50 = min(
                (s["ic50_uM"] for s in c["assay_summaries"] if s.get("ic50_uM")),
                default=None
            )
            ic50_str = f"  best IC50={best_ic50} µM" if best_ic50 else ""
            print(f"    CID {c['cid']:<10} {c['name'][:40]:<40} "
                  f"active in: {active_aids or '—'}{ic50_str}")

    # ── Step 4: Register via API ──────────────────────────────────────────────
    print(f"\n📦  Step 4 — {'Previewing' if dry else 'Registering'} compounds …")

    manifest = {
        "timestamp":   datetime.now(timezone.utc).isoformat(),
        "source_file": str(xl_path.resolve()),
        "api_base_url": base_url,
        "dry_run":     dry,
        "n_compounds_found":    len(compounds),
        "n_active_in_any_assay": active_in_any,
        "registered":  [],
        "skipped":     [],
        "errors":      [],
    }

    ok = skip = err = 0
    for c in compounds:
        cid   = c["cid"]
        name  = c["name"]
        smiles = c["smiles"]
        tags  = c["tags"]

        active_aids = [s["aid"] for s in c["assay_summaries"] if s.get("outcome") == "active"]
        best_ic50   = min(
            (s["ic50_uM"] for s in c["assay_summaries"] if s.get("ic50_uM")),
            default=None
        )
        status_str = (f"ACTIVE ({', '.join(active_aids)}) IC50={best_ic50} µM"
                      if active_aids else "inactive/not-tested")
        print(f"  ↑ CID {cid:<10} {name[:38]:<38} {status_str}")

        if not dry:
            result = post_compound(base_url, name, smiles, tags, args.delay)
            if result:
                api_id = result.get("_id", "")
                manifest["registered"].append({
                    "cid": cid, "name": name, "api_id": api_id,
                    "tags": tags, "assay_summaries": c["assay_summaries"],
                    "mw": c.get("mw"), "xlogp": c.get("xlogp"), "tpsa": c.get("tpsa"),
                })
                ok += 1
            else:
                manifest["errors"].append({"cid": cid, "name": name})
                err += 1
        else:
            manifest["registered"].append({
                "cid": cid, "name": name, "dry_run": True,
                "tags": tags, "assay_summaries": c["assay_summaries"],
            })
            ok += 1

    # ── Manifest ──────────────────────────────────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    manifest_path = out_dir / f"compound_manifest_{ts}.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, default=str)

    print(f"\n{'='*62}")
    print(f"  Compound registration complete!")
    print(f"  Registered : {ok}")
    print(f"  Errors     : {err}")
    print(f"  Manifest   : {manifest_path}")
    print(f"{'='*62}\n")


if __name__ == "__main__":
    main()
