import pandas as pd
import json
from collections import Counter
from pathlib import Path

def analyze_insights():
    df = pd.read_csv("outputs/tri_results_master.csv")
    df = df[df["relevant"] == True].copy()
    
    # Deduplicate by title to match UI
    df = df.drop_duplicates(subset=["title", "question_id"])
    
    # 1. Growth over time
    growth = df.groupby(["year", "question_id"]).size().unstack().fillna(0)
    print("Growth by year and question:")
    print(growth)
    
    # 2. Key topics from directional claims
    def extract_keywords(text):
        if pd.isna(text): return []
        text = text.lower()
        # Simple keyword extraction
        words = ["bias", "mitigation", "transparency", "accountability", "trust", "hallucination", "alignment", "safety", "robustness", "healthcare", "finance", "legal", "education", "reasoning", "cot", "self-explanation"]
        return [w for w in words if w in text]

    df["keywords"] = df["directional_claim"].apply(extract_keywords)
    
    # 3. Analyze each question
    insights = {}
    for qid in ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6"]:
        q_df = df[df["question_id"] == qid]
        all_keywords = [k for sub in q_df["keywords"] for k in sub]
        top_keywords = Counter(all_keywords).most_common(5)
        
        # Recent trends (2025-2026)
        recent = q_df[q_df["year"] >= 2025]
        
        insights[qid] = {
            "count": len(q_df),
            "top_keywords": top_keywords,
            "recent_count": len(recent),
            "sample_claims": q_df["directional_claim"].dropna().sample(min(3, len(q_df))).tolist() if len(q_df) > 0 else []
        }
        
    # Output to a file for review
    with open("scratch/analysis_insights.json", "w") as f:
        json.dump(insights, f, indent=2)

analyze_insights()
