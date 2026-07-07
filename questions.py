#!/usr/bin/env python3
"""
questions.py
Directional assignment over six questions (Q1–Q6) with NO caps or score thresholds.
Reads the prefiltered file produced by tri_prefilter_E0E2.py.

Inputs:
  --input  (default: outputs/prefilter_kept.csv)

Outputs (default: outputs/):
  - outputs/tri_results_master.csv
  - outputs/tri_results_Q1.csv ... tri_results_Q6.csv   (relevant-only per question)
  - outputs/tri_report.md                                (counts per question + listing)
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

import pandas as pd
import requests
from tqdm import tqdm

# Six strict, directional questions (paired opposites)
QUESTIONS: List[Dict[str, str]] = [
    # Cluster 1: Fairness/Bias ↔ Explainability
    {"id": "Q1", "cluster": "Fairness↔Explainability", "subcluster": "F→E",
     "query": "Does the paper show or argue that fairness/bias concerns motivate, drive, or shape explainability/XAI methods (i.e., explanations developed in response to fairness/bias needs)?"},
    {"id": "Q2", "cluster": "Fairness↔Explainability", "subcluster": "E→F",
     "query": "Does the paper show that explainability/XAI techniques are used to detect, measure, or mitigate bias/unfairness (i.e., explanations applied to fairness evaluation/mitigation)?"},
    # Cluster 2: Fairness/Bias ↔ LLMs
    {"id": "Q3", "cluster": "Fairness↔LLMs", "subcluster": "F→L",
     "query": "Does the paper define or operationalize fairness/bias concerns specifically for LLMs (e.g., fairness metrics/datasets/harms/constraints in LLM settings)?"},
    {"id": "Q4", "cluster": "Fairness↔LLMs", "subcluster": "L→F",
     "query": "Does the paper show LLMs affecting, amplifying, or addressing fairness/bias/discrimination (measured effects or mitigation on LLM outputs/behaviors)?"},
    # Cluster 3: Explainability/XAI ↔ LLMs
    {"id": "Q5", "cluster": "Explainability↔LLMs", "subcluster": "E→L",
     "query": "Does the paper apply explainability/interpretability methods to analyze or interpret LLM behavior (e.g., attribution, counterfactuals, probing, TCAV)?"},
    {"id": "Q6", "cluster": "Explainability↔LLMs", "subcluster": "L→E",
     "query": "Does the paper show LLMs advancing or challenging explainability (e.g., self-explanations/CoT, attribution faithfulness, explanation generation limits)?"},
]

SYSTEM_PROMPT = """You are an expert research assistant screening academic papers by directional questions.

Return a STRICT JSON object:
{
  "question_id": "Q1|Q2|Q3|Q4|Q5|Q6",
  "relevant": true/false,                      // true only if the paper answers THIS question's direction
  "reason": "<one concise sentence>",          // why/why not for THIS direction
  "mentions_fairness": true/false,
  "mentions_xai": true/false,
  "mentions_llm": true/false,
  "directional_claim": "<short directional summary if relevant>"
}
Rules:
- Be directional: for Q1 it's fairness→explainability; for Q2 it's explainability→fairness; Q3 fairness→LLMs; Q4 LLMs→fairness; Q5 explainability→LLMs; Q6 LLMs→explainability.
- If unclear, set relevant=false.
- Output ONLY the JSON. No extra text.
"""

USER_PROMPT_TEMPLATE = """QUESTION: {qid} ({cluster} / {subc})
Q-text: {qtext}

Paper:
Title: {title}
Abstract: {abstract}

Respond with the STRICT JSON schema specified by the system message.
"""

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
        # OpenAI-compatible response format
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

def ask_all_questions(row: pd.Series, model: str) -> List[Dict[str, Any]]:
    title = str(row.get("title", ""))[:8000]
    abstract = str(row.get("abstract", ""))[:12000]
    res = []
    for q in QUESTIONS:
        user_prompt = USER_PROMPT_TEMPLATE.format(
            qid=q["id"], cluster=q["cluster"], subc=q["subcluster"], qtext=q["query"],
            title=title, abstract=abstract
        )
        r = call_llm(SYSTEM_PROMPT, user_prompt, model=model)
        parsed = parse_json(r, {
            "question_id": q["id"], "relevant": False, "reason": "LLM error",
            "mentions_fairness": False, "mentions_xai": False, "mentions_llm": False,
            "directional_claim": ""
        })
        parsed["question_id"] = parsed.get("question_id") or q["id"]
        parsed["_cluster"] = q["cluster"]
        parsed["_subcluster"] = q["subcluster"]
        parsed["_title"] = row.get("title", "")
        parsed["_abstract"] = row.get("abstract", "")
        parsed["_year"] = row.get("year", "")
        parsed["_venue"] = row.get("venue", "")
        parsed["_url"] = row.get("url", "")
        res.append(parsed)
    return res

def screen(df: pd.DataFrame, model: str) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Screening Q1–Q6"):
        results.extend(ask_all_questions(row, model))
    return results

def to_bool(x: Any) -> bool:
    if isinstance(x, bool): return x
    if isinstance(x, str): return x.strip().lower() in {"true", "yes", "y", "1"}
    return bool(x)

def write_outputs(results: List[Dict[str, Any]], out_dir: Path) -> Tuple[Path, Path, List[Path]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for r in results:
        rows.append({
            "question_id": r.get("question_id", ""),
            "cluster": r.get("_cluster", ""),
            "subcluster": r.get("_subcluster", ""),
            "relevant": to_bool(r.get("relevant", False)),
            "reason": str(r.get("reason", "")),
            "directional_claim": str(r.get("directional_claim", "")),
            "mentions_fairness": to_bool(r.get("mentions_fairness", False)),
            "mentions_xai": to_bool(r.get("mentions_xai", False)),
            "mentions_llm": to_bool(r.get("mentions_llm", False)),
            "title": r.get("_title", ""),
            "abstract": r.get("_abstract", ""),
            "year": r.get("_year", ""),
            "venue": r.get("_venue", ""),
            "url": r.get("_url", "")
        })
    df = pd.DataFrame(rows)

    master_csv = out_dir / "tri_results_master.csv"
    df.to_csv(master_csv, index=False)

    per_q_paths: List[Path] = []
    counts = []
    for q in QUESTIONS:
        qdf = df[(df["question_id"] == q["id"]) & (df["relevant"] == True)].copy()
        qpath = out_dir / f"tri_results_{q['id']}.csv"
        qdf.to_csv(qpath, index=False)
        per_q_paths.append(qpath)
        counts.append((q["id"], len(qdf)))

    md_path = out_dir / "tri_report.md"
    with md_path.open("w", encoding="utf-8") as f:
        f.write("# Triangle screening (directional; no thresholds)\n\n")
        f.write("## Counts per question (all relevant papers included)\n\n")
        for qid, n in counts:
            f.write(f"- {qid}: {n} relevant papers\n")
        f.write("\n")

        f.write("## Clusters\n\n")
        for cluster in ["Fairness↔Explainability", "Fairness↔LLMs", "Explainability↔LLMs"]:
            f.write(f"### {cluster}\n\n")
            sub = (["F→E","E→F"] if cluster == "Fairness↔Explainability"
                   else ["F→L","L→F"] if cluster == "Fairness↔LLMs"
                   else ["E→L","L→E"])
            for s in sub:
                subdf = df[(df["cluster"] == cluster) & (df["subcluster"] == s) & (df["relevant"] == True)]
                f.write(f"**{s}** — {len(subdf)} papers\n\n")
                for _, r in subdf.iterrows():
                    meta = " | ".join([str(x) for x in [r["year"], r["venue"], r["url"]] if str(x)])
                    f.write(f"- **{r['title']}**  \n")
                    if meta: f.write(f"  *{meta}*  \n")
                    if r["directional_claim"]:
                        f.write(f"  _Directional claim:_ {r['directional_claim']}  \n")
                f.write("\n")

    return master_csv, md_path, per_q_paths

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=str, default="outputs/prefilter_kept.csv",
                    help="Path to prefiltered CSV (from tri_prefilter_E0E2.py).")
    ap.add_argument("--model", type=str, default="llama4:16x17b",
                    help="Model name on Open WebUI (e.g., llama4:16x17b, qwen3.5:122b).")
    ap.add_argument("--outdir", type=str, default="outputs", help="Output directory.")
    args = ap.parse_args()

    inp = Path(args.input)
    outdir = Path(args.outdir)

    if not OPENWEBUI_API_KEY:
        raise EnvironmentError("Missing OPENWEBUI_API_KEY. Set it before running this script.")

    print(f"[INFO] Loading {inp} …")
    df = load_dataframe(inp)

    print(f"[INFO] Screening {len(df)} kept papers against Q1–Q6 with '{args.model}' …")
    results = screen(df, model=args.model)

    master_csv, md_path, per_q_paths = write_outputs(results, outdir)
    print(f"[DONE] Wrote:\n  - {master_csv}\n  - {md_path}")
    for p in per_q_paths:
        print(f"  - {p}")

if __name__ == "__main__":
    main()
