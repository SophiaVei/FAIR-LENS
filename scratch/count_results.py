import pandas as pd
from pathlib import Path
import re

# 1. Parse prefilter_report.md for E0-E2 counts
report_path = Path("outputs/prefilter_report.md")
e0 = e1 = e2 = 0
if report_path.exists():
    text = report_path.read_text(encoding="utf-8")
    # Find lines like "*codes:* E0,E2"
    matches = re.findall(r"\*codes:\*\s*(.*)", text)
    for m in matches:
        codes = [c.strip() for c in m.split(",")]
        if "E0" in codes: e0 += 1
        if "E1" in codes: e1 += 1
        if "E2" in codes: e2 += 1

print(f"E0: {e0}")
print(f"E1: {e1}")
print(f"E2: {e2}")

# 2. Parse tri_results_master.csv for relevant count
master_path = Path("outputs/tri_results_master.csv")
if master_path.exists():
    df = pd.read_csv(master_path)
    # The master file has rows per question. We need unique papers.
    # Usually the pipeline counts unique papers that have at least one question relevant=True.
    
    unique_all = df.drop_duplicates(subset=["title"])
    relevant_df = df[df["relevant"] == True]
    unique_relevant = relevant_df.drop_duplicates(subset=["title"])
    
    print(f"Total rows in master: {len(df)}")
    print(f"Unique papers in master: {len(unique_all)}")
    print(f"Relevant rows: {len(relevant_df)}")
    print(f"Unique relevant papers: {len(unique_relevant)}")
    print(f"Irrelevant (dropped by LLM): {len(unique_all) - len(unique_relevant)}")
