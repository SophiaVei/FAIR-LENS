import pandas as pd
import json
import re
from collections import Counter

def analyze_and_export():
    df = pd.read_csv("outputs/tri_results_master.csv")
    df = df[df["relevant"] == True].copy()
    
    # Deduplicate papers (one paper can have multiple questions)
    papers = df.drop_duplicates(subset=["title"]).copy()
    
    # 1. Multi-directionality (Intersectionality)
    intersect_counts = df.groupby("title").size().reset_index(name="q_count")
    intersect_dist = Counter(intersect_counts["q_count"])
    intersection_data = [{"count": str(k), "value": v} for k, v in sorted(intersect_dist.items())]

    # 2. Taxonomy Definition
    taxonomy = {
        "Domains": ["medical", "clinical", "healthcare", "finance", "legal", "education", "hiring", "recruitment", "justice", "security", "software", "scientific"],
        "XAI Methods": ["shap", "lime", "attention", "saliency", "integrated gradients", "counterfactual", "rationale", "probing", "mechanistic", "feature attribution", "attribution"],
        "Fairness Concepts": ["gender", "race", "ethnic", "age", "multilingual", "language", "geographic", "socioeconomic", "stereotyp", "toxicity", "bias", "parity", "equality"],
        "Models": ["gpt", "llama", "bert", "roberta", "mistral", "claude", "gemini", "t5", "palm", "transformer", "bloom"],
        "Paper Type": ["benchmark", "dataset", "mitigation", "audit", "survey", "human study", "experiment", "framework"]
    }

    def extract_keywords(text):
        text = str(text).lower()
        found = {cat: [] for cat in taxonomy}
        for cat, keywords in taxonomy.items():
            for kw in keywords:
                if kw in text:
                    found[cat].append(kw)
        return found

    # 3. Model Evolution (Unique papers per year mentioning a model)
    model_keywords = taxonomy["Models"]
    evolution_data = []
    years = sorted(papers["year"].dropna().unique())
    for y in years:
        year_papers = papers[papers["year"] == y]
        counts = {"year": int(y)}
        for m in model_keywords:
            # Count papers where model name appears in title or abstract
            match_count = year_papers.apply(lambda r: m in str(r["title"]).lower() or m in str(r["abstract"]).lower(), axis=1).sum()
            counts[m] = int(match_count)
        evolution_data.append(counts)

    # 4. Diagnostic vs Proactive Split
    # Proactive: Q1, Q3
    # Diagnostic: Q2, Q4, Q5, Q6
    def get_focus(qid):
        if qid in ["Q1", "Q3"]: return "Proactive (Design)"
        return "Diagnostic (Audit)"
    
    df["focus"] = df["question_id"].apply(get_focus)
    focus_evolution = df.groupby(["year", "focus"]).size().unstack().fillna(0).reset_index()
    focus_evolution = focus_evolution.rename(columns={"year": "year"})
    focus_evolution_data = focus_evolution.to_dict(orient="records")

    # 5. Venue Type Mapping
    venue_map = {
        "NLP": ["acl", "emnlp", "naacl", "tacl", "coling", "lrec"],
        "HCI/Social": ["chi", "cscw", "uist", "tochi", "human-computer"],
        "Fairness/Ethics": ["facct", "aies", "ethics", "equity", "responsible"],
        "General AI/ML": ["neurips", "iclr", "icml", "aaai", "ijcai", "kdd", "cvpr", "iccv"],
        "Application": ["medical", "health", "legal", "law", "finance", "education", "software", "scientific"]
    }

    def categorize_venue(v):
        v = str(v).lower()
        for cat, keywords in venue_map.items():
            for kw in keywords:
                if kw in v: return cat
        return "Other"

    papers["venue_cat"] = papers["venue"].apply(categorize_venue)
    venue_dist = papers["venue_cat"].value_counts().reset_index()
    venue_dist.columns = ["name", "value"]
    venue_dist_data = venue_dist.to_dict(orient="records")

    # 6. Aggregate results by Question ID
    q_topic_data = {}
    for qid in ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6"]:
        q_papers = df[df["question_id"] == qid].copy()
        q_stats = {cat: Counter() for cat in taxonomy}
        for _, row in q_papers.iterrows():
            ext = extract_keywords(str(row["title"]) + " " + str(row["abstract"]) + " " + str(row["directional_claim"]))
            for cat, kws in ext.items():
                q_stats[cat].update(kws)
        q_topic_data[qid] = {cat: [{"name": k, "value": v} for k, v in count.most_common(8)] for cat, count in q_stats.items()}

    # 7. Global Trends (Top keywords across everything)
    global_stats = {cat: Counter() for cat in taxonomy}
    for _, row in papers.iterrows():
        ext = extract_keywords(str(row["title"]) + " " + str(row["abstract"]))
        for cat, kws in ext.items():
            global_stats[cat].update(kws)
    global_trends = {cat: [{"name": k, "value": v} for k, v in count.most_common(12)] for cat, count in global_stats.items()}

    # 8. Combined JSON
    output = {
        "intersection_dist": intersection_data,
        "question_topics": q_topic_data,
        "global_trends": global_trends,
        "model_evolution": evolution_data,
        "focus_evolution": focus_evolution_data,
        "venue_distribution": venue_dist_data,
        "total_unique_papers": len(papers),
        "total_assignments": len(df)
    }

    with open("fair-lens-visualizer/src/data/dashboard_insights.json", "w") as f:
        json.dump(output, f, indent=2, default=str)
    
    # 8. Export papers for Explorer
    explorer_data = []
    for _, row in df.iterrows():
        explorer_data.append({
            "question_id": row["question_id"],
            "cluster": row["cluster"],
            "subcluster": row["subcluster"],
            "title": row["title"],
            "year": int(row["year"]) if not pd.isna(row["year"]) else None,
            "venue": str(row["venue"]),
            "url": str(row["url"]) if not pd.isna(row["url"]) else "",
            "directional_claim": row["directional_claim"],
            "mentions_fairness": bool(row["mentions_fairness"]),
            "mentions_xai": bool(row["mentions_xai"]),
            "mentions_llm": bool(row["mentions_llm"])
        })
    
    with open("fair-lens-visualizer/public/fairlens_papers.json", "w") as f:
        json.dump(explorer_data, f, indent=2)

    print("Exported enhanced dashboard_insights.json and fairlens_papers.json.")

if __name__ == "__main__":
    analyze_and_export()
