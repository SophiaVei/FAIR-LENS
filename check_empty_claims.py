#!/usr/bin/env python3
"""Check papers with empty directional_claim"""

import json
from pathlib import Path
import pandas as pd

# Check JSON
json_path = Path("fair-lens-visualizer/public/fairlens_papers.json")
with json_path.open("r", encoding="utf-8") as f:
    papers = json.load(f)

empty_claims = [p for p in papers if not p.get("directional_claim", "").strip()]
print(f"Papers with empty directional_claim in JSON: {len(empty_claims)}")
print("\nPapers with empty claims:")
for paper in empty_claims:
    print(f"  - {paper['title'][:80]}...")
    print(f"    Question: {paper['question_id']}, Relevant: True (since it's in the JSON)")

# Check CSV
csv_path = Path("outputs/tri_results_master.csv")
df = pd.read_csv(csv_path)
df_relevant = df[df["relevant"] == True].copy()

# Check for empty directional_claim in relevant papers
empty_in_csv = df_relevant[df_relevant["directional_claim"].isna() | (df_relevant["directional_claim"].str.strip() == "")]
print(f"\n\nPapers with empty directional_claim in CSV (relevant=True): {len(empty_in_csv)}")
if len(empty_in_csv) > 0:
    print("\nEmpty claims in CSV:")
    for idx, row in empty_in_csv.iterrows():
        print(f"  - {row['title'][:80]}...")
        print(f"    Question: {row['question_id']}, Reason: {row['reason'][:100] if pd.notna(row['reason']) else 'N/A'}")

# Check if the wind power paper has claims in CSV
wind_power = df_relevant[df_relevant["title"].str.contains("wind power", case=False, na=False)]
print(f"\n\nWind power paper entries in CSV (relevant=True): {len(wind_power)}")
for idx, row in wind_power.iterrows():
    claim = row['directional_claim']
    print(f"  - Q{row['question_id']}: claim='{claim}' (length: {len(str(claim)) if pd.notna(claim) else 0})")

