#!/usr/bin/env python3
"""
LLM-powered screening over S4_tagged.csv to find:
"bias mitigation methods applied to large language models, including XAI".

- Reads:  data/lens/stages/S4_tagged.csv  (change --input if needed)
- Ranks with embeddings (MiniLM) to get top-K candidates
- Uses local LLM via Ollama (default model: 'mistral') to judge + extract
- Writes: outputs/bias_mitigation_results.csv and .md

Install deps:
  pip install pandas numpy sentence-transformers tqdm requests

Install + run a free local LLM:
  1) Install Ollama: https://ollama.com
  2) Pull a model:   ollama pull mistral
  3) (optional) try: ollama pull llama3.2

Run:
  python llm_screen_bias_mitigation.py \
    --input data/lens/stages/S4_tagged.csv \
    --model mistral \
    --top_k 80 \
    --min_score 70
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

import numpy as np
import pandas as pd
import requests
from tqdm import tqdm

# Embeddings
from sentence_transformers import SentenceTransformer


DEFAULT_QUERY = (
    "Identify papers that discuss bias mitigation methods applied to large language models "
    "(e.g., GPT/LLM/transformers) AND explicitly involve or mention explainable AI (XAI) "
    "or interpretability (e.g., feature attribution, counterfactuals, TCAV, model cards). "
    "Focus on concrete mitigation techniques, evaluation with fairness metrics, datasets, and LLMs."
)

SYSTEM_PROMPT = """You are an expert research assistant screening academic papers.
Given the title and abstract of a paper, decide if it discusses BIAS MITIGATION METHODS APPLIED TO LARGE LANGUAGE MODELS (LLMs),
*and* whether it involves EXPLAINABLE AI (XAI) or interpretability concepts.

Return a STRICT JSON object with these fields:
{
  "relevant": true/false,
  "reason": "<one concise sentence>",
  "mentions_xai": true/false,
  "mitigation_methods": ["<method1>", "<method2>", ...],  // empty if none
  "llms_or_models": ["<LLM/model names>", ...],           // empty if none
  "fairness_metrics": ["<metric names>", ...],            // empty if none
  "datasets": ["<dataset names>", ...],                   // empty if none
  "score": <0-100 integer>                                // confidence of relevance
}

Relevance definition:
- The paper must address LLMs (e.g., GPT, transformer-based, instruction-tuned models), not CV/audio-only models.
- It must include bias mitigation (e.g., debiasing prompts, data curation, counterfactual data augmentation, RLHF variants, representation balancing, post-processing, fairness-constrained decoding).
- Prefer papers that also use or discuss XAI/interpretability (e.g., feature attribution, counterfactual explanations, influence functions, TCAV, probing) in service of mitigation.

If unclear, set "relevant": false and explain why in "reason".
Output ONLY the JSON. No extra text.
"""

USER_PROMPT_TEMPLATE = """Paper:
Title: {title}
Abstract: {abstract}

Task: Does this paper describe *bias mitigation methods applied to LLMs*, and does it involve XAI/interpretability?
Respond with the STRICT JSON schema specified by the system message.
"""

def load_dataframe(path: Path) -> pd.DataFrame:
    if not path.exists():
        print(f"[ERROR] Input CSV not found: {path}", file=sys.stderr)
        sys.exit(1)
    df = pd.read_csv(path)
    # Ensure expected columns are present
    required = {"title", "abstract", "year", "venue", "url"}
    missing = required - set(df.columns)
    if missing:
        print(f"[WARN] Missing expected columns {missing} — continuing with what we have.")
        for m in missing:
            df[m] = ""
    return df

def build_corpus(df: pd.DataFrame) -> List[str]:
    texts = (df["title"].fillna("") + ". " + df["abstract"].fillna("")).tolist()
    return texts

def embed_texts(texts: List[str], model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> np.ndarray:
    model = SentenceTransformer(model_name)
    emb = model.encode(texts, show_progress_bar=True, convert_to_numpy=True, normalize_embeddings=True)
    return emb

def top_k_indices(query: str, corpus_emb: np.ndarray, embed_model: SentenceTransformer, k: int = 80) -> List[int]:
    q = embed_model.encode([query], convert_to_numpy=True, normalize_embeddings=True)[0]
    sims = (corpus_emb @ q)
    idx = np.argsort(-sims)[:k]
    return idx.tolist()

def call_ollama(prompt: str, model: str = "mistral", url: str = "http://localhost:11434/api/generate", timeout: int = 90) -> str:
    """
    Calls Ollama's /api/generate endpoint with a single prompt.
    Returns the concatenated response text.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        js = r.json()
        return js.get("response", "").strip()
    except Exception as e:
        return f"__ERROR__: {e}"

def extract_json_block(text: str) -> Dict[str, Any]:
    """
    Try to extract a JSON object from the LLM output robustly.
    """
    if text.startswith("__ERROR__"):
        return {"relevant": False, "reason": text, "mentions_xai": False,
                "mitigation_methods": [], "llms_or_models": [], "fairness_metrics": [],
                "datasets": [], "score": 0}

    # Try a simple JSON parse first
    try:
        return json.loads(text)
    except Exception:
        pass

    # Find the first {...} block
    m = re.search(r"\{.*\}", text, flags=re.S)
    if m:
        candidate = m.group(0)
        try:
            return json.loads(candidate)
        except Exception:
            # Try to sanitize typical trailing commas
            candidate2 = re.sub(r",\s*}", "}", candidate)
            candidate2 = re.sub(r",\s*]", "]", candidate2)
            try:
                return json.loads(candidate2)
            except Exception:
                return {"relevant": False, "reason": f"Could not parse JSON. Raw: {text[:400]}",
                        "mentions_xai": False, "mitigation_methods": [], "llms_or_models": [],
                        "fairness_metrics": [], "datasets": [], "score": 0}
    # Fallback
    return {"relevant": False, "reason": f"No JSON found. Raw: {text[:400]}",
            "mentions_xai": False, "mitigation_methods": [], "llms_or_models": [],
            "fairness_metrics": [], "datasets": [], "score": 0}

def screen_with_llm(
    df: pd.DataFrame,
    indices: List[int],
    model: str = "mistral",
) -> List[Dict[str, Any]]:
    rows = []
    for i in tqdm(indices, desc="LLM screening"):
        row = df.iloc[i]
        title = str(row.get("title", ""))[:8000]
        abstract = str(row.get("abstract", ""))[:12000]

        user_prompt = USER_PROMPT_TEMPLATE.format(title=title, abstract=abstract)
        # Compose a single prompt (Ollama supports just 'prompt' — we prepend system)
        full_prompt = f"<<SYS>>\n{SYSTEM_PROMPT}\n<</SYS>>\n\n{user_prompt}"

        resp = call_ollama(full_prompt, model=model)
        parsed = extract_json_block(resp)

        # attach bookkeeping
        parsed["_row_index"] = int(i)
        parsed["_title"] = row.get("title", "")
        parsed["_abstract"] = row.get("abstract", "")
        parsed["_year"] = row.get("year", "")
        parsed["_venue"] = row.get("venue", "")
        parsed["_url"] = row.get("url", "")
        rows.append(parsed)
    return rows

def to_bool(x: Any) -> bool:
    if isinstance(x, bool):
        return x
    if isinstance(x, str):
        return x.strip().lower() in {"true", "yes", "y", "1"}
    return bool(x)

def coerce_list(x: Any) -> List[str]:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return []
    if isinstance(x, list):
        return [str(t).strip() for t in x if str(t).strip()]
    if isinstance(x, str):
        try:
            j = json.loads(x)
            if isinstance(j, list):
                return [str(t).strip() for t in j if str(t).strip()]
        except Exception:
            # split on ; or , as last resort
            parts = re.split(r"[;,]", x)
            return [p.strip() for p in parts if p.strip()]
    return [str(x).strip()]

def write_outputs(
    results: List[Dict[str, Any]],
    out_dir: Path,
    min_score: int = 70
) -> Tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)

    # Normalize & frame
    norm_rows = []
    for r in results:
        norm_rows.append({
            "relevant": to_bool(r.get("relevant", False)),
            "reason": str(r.get("reason", "")),
            "mentions_xai": to_bool(r.get("mentions_xai", False)),
            "mitigation_methods": "; ".join(coerce_list(r.get("mitigation_methods", []))),
            "llms_or_models": "; ".join(coerce_list(r.get("llms_or_models", []))),
            "fairness_metrics": "; ".join(coerce_list(r.get("fairness_metrics", []))),
            "datasets": "; ".join(coerce_list(r.get("datasets", []))),
            "score": int(r.get("score", 0)) if str(r.get("score", "")).isdigit() else 0,
            "title": r.get("_title", ""),
            "abstract": r.get("_abstract", ""),
            "year": r.get("_year", ""),
            "venue": r.get("_venue", ""),
            "url": r.get("_url", "")
        })
    df = pd.DataFrame(norm_rows)
    df = df.sort_values(["relevant", "mentions_xai", "score"], ascending=[False, False, False])

    # Save CSV
    csv_path = out_dir / "bias_mitigation_results.csv"
    df.to_csv(csv_path, index=False)

    # Markdown report
    md_path = out_dir / "bias_mitigation_report.md"
    with md_path.open("w", encoding="utf-8") as f:
        f.write("# Bias mitigation in LLMs (screened with local LLM)\n\n")
        keep = df[(df["relevant"]) & (df["score"] >= min_score)]
        f.write(f"- Total screened by LLM: {len(df)}\n")
        f.write(f"- Kept (relevant & score ≥ {min_score}): {len(keep)}\n\n")

        for _, r in keep.iterrows():
            f.write(f"## {r['title']}\n")
            meta = []
            if r["year"]: meta.append(str(r["year"]))
            if r["venue"]: meta.append(str(r["venue"]))
            if r["url"]: meta.append(str(r["url"]))
            if meta:
                f.write(f"*{' | '.join(meta)}*\n\n")
            f.write(f"**Score:** {r['score']} | **Mentions XAI:** {r['mentions_xai']}\n\n")
            if r["mitigation_methods"]:
                f.write(f"**Mitigation methods:** {r['mitigation_methods']}\n\n")
            if r["fairness_metrics"]:
                f.write(f"**Fairness metrics:** {r['fairness_metrics']}\n\n")
            if r["llms_or_models"]:
                f.write(f"**LLMs/Models:** {r['llms_or_models']}\n\n")
            if r["datasets"]:
                f.write(f"**Datasets:** {r['datasets']}\n\n")
            if r["reason"]:
                f.write(f"**LLM justification:** {r['reason']}\n\n")
            f.write("\n---\n\n")

    return csv_path, md_path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=str, default="data/lens/stages/S4_tagged.csv",
                    help="Path to the curated CSV (S4_tagged.csv or data/raw/lens.csv).")
    ap.add_argument("--query", type=str, default=DEFAULT_QUERY, help="Semantic search query.")
    ap.add_argument("--embed_model", type=str, default="sentence-transformers/all-MiniLM-L6-v2",
                    help="SentenceTransformer model for embeddings.")
    ap.add_argument("--model", type=str, default="mistral",
                    help="Ollama model name (e.g., mistral, llama3.2, etc.)")
    ap.add_argument("--top_k", type=int, default=80, help="Top-K candidates to send to the LLM.")
    ap.add_argument("--min_score", type=int, default=70, help="Minimum score to mark as strong keep in the report.")
    ap.add_argument("--outdir", type=str, default="outputs", help="Output directory.")
    args = ap.parse_args()

    input_path = Path(args.input)
    outdir = Path(args.outdir)

    print(f"[INFO] Loading {input_path} …")
    df = load_dataframe(input_path)
    corpus_texts = build_corpus(df)

    print(f"[INFO] Embedding {len(corpus_texts)} papers with {args.embed_model} …")
    embed_model = SentenceTransformer(args.embed_model)
    corpus_emb = embed_texts(corpus_texts, model_name=args.embed_model)

    print(f"[INFO] Selecting top-{args.top_k} by semantic similarity for query:\n  {args.query}\n")
    top_idx = top_k_indices(args.query, corpus_emb, embed_model, k=args.top_k)

    print(f"[INFO] Screening {len(top_idx)} candidates with Ollama model '{args.model}' …")
    results = screen_with_llm(df, top_idx, model=args.model)

    csv_path, md_path = write_outputs(results, outdir, min_score=args.min_score)
    print(f"[DONE] Wrote:\n  - {csv_path}\n  - {md_path}")
    print("\nTip: open the Markdown report to skim the strongest candidates quickly.")

if __name__ == "__main__":
    main()
