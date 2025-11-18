# prepare_fairlens_json.py
import pandas as pd
import json
from pathlib import Path

INPUT_CSV = Path(r"C:\Users\Sofia\PycharmProjects\FAIR-LEARN\outputs\tri_results_master.csv")
OUTPUT_JSON = Path("public/fairlens_papers.json")

def main():
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"{INPUT_CSV} not found")

    df = pd.read_csv(INPUT_CSV)

    # Keep only rows marked as relevant
    if "relevant" in df.columns:
        df = df[df["relevant"] == True].copy()

    # Build records
    records = []
    for _, row in df.iterrows():
        rec = {
            "question_id": str(row.get("question_id", "")).strip(),   # Q1–Q6
            "cluster": str(row.get("cluster", "")).strip(),
            "subcluster": str(row.get("subcluster", "")).strip(),
            "title": str(row.get("title", "")).strip(),
            "year": int(row["year"]) if "year" in df.columns and pd.notna(row["year"]) else None,
            "venue": str(row.get("venue", "")).strip(),
            "url": str(row.get("url", "")).strip(),
            "directional_claim": str(row.get("directional_claim", "")).strip(),
            "mentions_fairness": bool(row.get("mentions_fairness", False)),
            "mentions_xai": bool(row.get("mentions_xai", False)),
            "mentions_llm": bool(row.get("mentions_llm", False)),
        }
        records.append(rec)

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(records)} records to {OUTPUT_JSON}")

if __name__ == "__main__":
    main()
