#!/usr/bin/env python3
"""
exclude_final.py
Conservative, content-based prefilter using an LLM (via Ollama) before directional screening.

Rules (exclude ONLY if clearly true; if uncertain -> KEEP):
  E0 – Not actually about transformer LLMs (GPT-like; transformer LMs).
  E1 – No substantive fairness/bias AND no substantive explainability/XAI
       (mere mentions without operationalization: no method/metric/dataset/experiment).
  E2 – Commentary-only for our scope (editorial/opinion/news/tutorial/ethics-only)
       with NO technical method/evaluation linking fairness/XAI to LLMs.

Inputs:
  --input  (default: data/lens/stages/S4_tagged.csv)

Outputs (default: outputs/):
  - outputs/prefilter_kept.csv
  - outputs/prefilter_dropped.csv
  - outputs/prefilter_report.md
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, Any, List

import pandas as pd
import requests
from tqdm import tqdm

EXCLUSION_CRITERIA_TEXT = (
    "Exclude ONLY if an item clearly matches at least ONE:\n"
    "E0: Not actually about transformer large language models (GPT-like; transformer LMs). "
    "Examples: rule-based/chatbot systems, non-ML uses of 'language model', non-transformer systems without LLMs.\n"
    "E1: No substantive fairness/bias AND no substantive explainability/XAI. Mentions alone are insufficient—look for operationalization "
    "(methods, metrics, experiments, datasets, or concrete tasks).\n"
    "E2: Commentary-only for our scope (editorial/opinion/news/tutorial/ethics-only) with NO technical method/evaluation linking fairness/XAI to LLMs.\n"
    "If uncertain, do NOT exclude."
)

PREFILTER_SYSTEM_PROMPT = f"""You are filtering papers conservatively before a focused review.

Return a STRICT JSON with fields:
{{
  "exclude": true/false,                 // true only if it clearly hits ≥1 exclusion
  "reasons": ["E0"|"E1"|"E2", ...],      // list of matched codes; empty if none
  "note": "<very short justification>"
}}

Content-based rules:
{EXCLUSION_CRITERIA_TEXT}

Operationalization signals to KEEP:
- Presence of technical method(s), algorithms, datasets, metrics, experiments, or evaluation tied to fairness/XAI/LLMs.

If uncertain, set "exclude": false.
Output ONLY the JSON.
"""

PREFILTER_USER_TEMPLATE = """Paper:
Title: {title}
Abstract: {abstract}
Apply the exclusion rules and respond with the STRICT JSON schema."""

# ---- LLM backend configuration ----
# Set your API key in PowerShell:
#   $env:OPENWEBUI_API_KEY = "your_api_key"
OPENWEBUI_API_KEY = os.getenv("OPENWEBUI_API_KEY", "").strip()
OPENWEBUI_BASE_URL = os.getenv("OPENWEBUI_BASE_URL", "https://filos.csd.auth.gr").strip().rstrip("/")

def call_llm(system_prompt: str, user_prompt: str,
             model: str = "llama4:16x17b",
             url: str = None, timeout: int = 300) -> str:
    """
    Call the Open WebUI server at filos.csd.auth.gr using its
    OpenAI-compatible /api/chat/completions endpoint.
    """
    if not OPENWEBUI_API_KEY:
        return "__ERROR__: Missing OPENWEBUI_API_KEY environment variable."

    if url is None:
        url = f"{OPENWEBUI_BASE_URL}/api/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENWEBUI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        "stream": False,
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=timeout)
        r.raise_for_status()
        js = r.json()
        return js["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"__ERROR__: {e}"

def parse_json(text: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
    if text.startswith("__ERROR__"):
        return fallback
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{.*\}", text, flags=re.S)
    if m:
        candidate = m.group(0)
        for cand in [candidate,
                     re.sub(r",\s*}", "}", candidate),
                     re.sub(r",\s*]", "]", candidate)]:
            try:
                return json.loads(cand)
            except Exception:
                continue
    return fallback

def load_dataframe(path: Path) -> pd.DataFrame:
    if not path.exists():
        print(f"[ERROR] Input CSV not found: {path}", file=sys.stderr)
        sys.exit(1)
    df = pd.read_csv(path)
    for col in ["title", "abstract", "year", "venue", "url"]:
        if col not in df.columns:
            df[col] = ""
    return df

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=str, default="data/lens/stages/S4_tagged.csv",
                    help="Path to curated CSV (S4_tagged.csv or data/raw/lens.csv).")
    ap.add_argument("--model", type=str, default="llama4:16x17b",
                    help="Model name on Open WebUI (e.g., llama4:16x17b, qwen3.5:122b).")
    ap.add_argument("--outdir", type=str, default="outputs",
                    help="Output directory for prefilter results.")
    args = ap.parse_args()

    inp = Path(args.input)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    if not OPENWEBUI_API_KEY:
        raise EnvironmentError("Missing OPENWEBUI_API_KEY. Set it before running this script.")

    print(f"[INFO] Loading {inp} …")
    df = load_dataframe(inp)

    kept_rows: List[Dict[str, Any]] = []
    dropped_rows: List[Dict[str, Any]] = []

    print(f"[INFO] Pre-filtering {len(df)} papers with E0–E2 (conservative)…")
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Prefilter E0–E2"):
        title = str(row.get("title", ""))[:8000]
        abstract = str(row.get("abstract", ""))[:12000]
        user_prompt = PREFILTER_USER_TEMPLATE.format(title=title, abstract=abstract)
        resp = call_llm(PREFILTER_SYSTEM_PROMPT, user_prompt, model=args.model)
        parsed = parse_json(resp, {"exclude": False, "reasons": [], "note": "LLM error/uncertain; kept"})
        exclude = bool(parsed.get("exclude", False))
        codes = ",".join(parsed.get("reasons", []))
        note = parsed.get("note", "")

        record = dict(row)
        record["prefilter_exclusion"] = exclude
        record["prefilter_codes"] = codes
        record["prefilter_note"] = note

        if exclude:
            dropped_rows.append(record)
        else:
            kept_rows.append(record)

    kept_df = pd.DataFrame(kept_rows)
    dropped_df = pd.DataFrame(dropped_rows)

    kept_path = outdir / "prefilter_kept.csv"
    drop_path = outdir / "prefilter_dropped.csv"
    kept_df.to_csv(kept_path, index=False)
    dropped_df.to_csv(drop_path, index=False)

    # Simple report
    md = outdir / "prefilter_report.md"
    with md.open("w", encoding="utf-8") as f:
        f.write("# Prefilter report (content-based E0–E2)\n\n")
        f.write("**Exclusion rules (applied conservatively; uncertainty -> keep):**\n\n")
        f.write("- E0: Not actually about transformer LLMs (GPT-like)\n")
        f.write("- E1: No substantive fairness/bias and no substantive explainability/XAI\n")
        f.write("- E2: Commentary-only; no technical method/eval linking fairness/XAI to LLMs\n\n")
        f.write(f"- Total input: {len(df)}\n")
        f.write(f"- Kept: {len(kept_df)}\n")
        f.write(f"- Dropped: {len(dropped_df)}\n\n")
        if not dropped_df.empty:
            f.write("## Dropped (id/title)\n\n")
            show_cols = [c for c in ["id","lens_id","doi","year","venue","title","prefilter_codes","prefilter_note"] if c in dropped_df.columns]
            for _, r in dropped_df.iterrows():
                title_show = str(r.get("title",""))[:140]
                codes = r.get("prefilter_codes","")
                note = r.get("prefilter_note","")
                ident = r.get("doi") or r.get("lens_id") or r.get("id") or ""
                f.write(f"- **{title_show}** — {ident}  \n")
                if codes: f.write(f"  *codes:* {codes}  \n")
                if note:  f.write(f"  *note:* {note}  \n")
    print(f"[DONE] Wrote:\n  - {kept_path}\n  - {drop_path}\n  - {md}")

if __name__ == "__main__":
    main()
