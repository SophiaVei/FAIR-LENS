#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
make_fairlens_evidence_table.py

Creates an enriched FAIR-LENS Evidence Table figure.

Input:
    outputs/fairlens_techniques/technique_summary_by_goal.csv

Output:
    outputs/figures/fairlens_evidence_table_enriched.png
    outputs/figures/fairlens_evidence_table_enriched.pdf

The figure is intentionally functional rather than final-design.
You can later beautify it in Canva.
"""

from __future__ import annotations

import argparse
import math
import re
import textwrap
from collections import Counter
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
import pandas as pd


GOAL_INFO: Dict[str, Dict[str, object]] = {
    "Q1": {
        "axis": "Accountability",
        "abbr": "Ju",
        "goal": "Justification",
        "direction": "Fairness -> Explainability",
        "role": "Assistant",
        "meaning": (
            "Fairness or bias concerns justify the need for explanations, "
            "transparency, contestability, or trustworthy decision support."
        ),
    },
    "Q2": {
        "axis": "Accountability",
        "abbr": "Di",
        "goal": "Diagnosis",
        "direction": "Explainability -> Fairness",
        "role": "Auditor",
        "meaning": (
            "Explanation methods diagnose, detect, localize, or mitigate unfairness, "
            "biased cues, or proxy effects."
        ),
    },
    "Q3": {
        "axis": "Alignment",
        "abbr": "Op",
        "goal": "Operationalization",
        "direction": "Fairness -> LLMs",
        "role": "Assistant",
        "meaning": (
            "Fairness is translated into LLM-specific benchmarks, prompts, "
            "evaluation protocols, alignment objectives, monitoring, or design requirements."
        ),
    },
    "Q4": {
        "axis": "Alignment",
        "abbr": "Im",
        "goal": "Impact",
        "direction": "LLMs -> Fairness",
        "role": "Auditor",
        "meaning": (
            "LLMs are examined for their effects on fairness, including stereotypes, "
            "toxicity, refusal asymmetries, group disparities, or unequal service quality."
        ),
    },
    "Q5": {
        "axis": "Visibility",
        "abbr": "In",
        "goal": "Inspection",
        "direction": "Explainability -> LLMs",
        "role": "Auditor",
        "meaning": (
            "Explainability or interpretability methods inspect LLM prompts, outputs, "
            "representations, activations, mechanisms, or behaviors."
        ),
    },
    "Q6": {
        "axis": "Visibility",
        "abbr": "Ge",
        "goal": "Generation",
        "direction": "LLMs -> Explainability",
        "role": "Assistant",
        "meaning": (
            "LLMs generate, translate, summarize, evaluate, mediate, or complicate "
            "explanations and rationales."
        ),
    },
}


AXES = {
    "Accountability": {
        "subtitle": "Fairness <-> Explainability",
        "color": "#7068BF",
        "light": "#ECEAF8",
    },
    "Alignment": {
        "subtitle": "Fairness <-> LLMs",
        "color": "#5C938B",
        "light": "#E8F2F0",
    },
    "Visibility": {
        "subtitle": "Explainability <-> LLMs",
        "color": "#D97A2B",
        "light": "#FFF0E2",
    },
}


ROLE_COLORS = {
    "Assistant": "#D96F00",
    "Auditor": "#4B00D8",
}

GENERIC_TECHNIQUE_NAMES = {
    "xai",
    "explainable ai",
    "explainable ai techniques",
    "explainable ai (xai",
    "large language model",
    "large language models",
    "large language models (llms",
    "llm",
    "llms",
    "visual explanation generation",
    "bias mitigation",
    "fairness evaluation",
    "algorithmic bias evaluation",
    "accountability frameworks",
    "adaptive ethical frameworks",
    "xai principles",
}

GENERIC_TECHNIQUE_PATTERNS = [
    r"^explainable ai(?: \(xai\))?(?: techniques?)?$",
    r"^large language models?(?: \(llms?\))?$",
    r"^bias mitigation$",
    r"^fairness evaluation$",
    r"^algorithmic bias evaluation$",
    r"^accountability frameworks?$",
    r"^adaptive ethical frameworks?$",
    r"^xai principles?$",
]

Q5_INSPECTION_PATTERNS = [
    r"\bshap\b",
    r"\blime\b",
    r"grad-?cam",
    r"integrated gradients?",
    r"saliency",
    r"attention",
    r"feature attribution",
    r"\btcav\b",
    r"activation patching",
    r"probing",
    r"mechanistic interpret",
    r"counterfactual",
    r"explanation method",
    r"interpret",
    r"inspect",
]

Q1_JUSTIFICATION_PATTERNS = [
    r"model cards?",
    r"datasheets?",
    r"counterfactual",
    r"federated learning",
    r"privacy-preserving",
    r"fairness constraints?",
    r"accountability",
    r"contestability",
    r"recourse",
    r"transparency",
    r"explanation interface",
]

Q1_EXCLUDE_PATTERNS = [
    r"\bshap\b",
    r"\blime\b",
    r"grad-?cam",
    r"integrated gradients?",
    r"saliency",
    r"attention visualization",
    r"feature attribution",
    r"\btcav\b",
]

Q2_DIAGNOSIS_PATTERNS = [
    r"\bshap\b",
    r"\blime\b",
    r"grad-?cam",
    r"integrated gradients?",
    r"saliency",
    r"attention",
    r"feature attribution",
    r"\btcav\b",
    r"counterfactual",
    r"demographic parity",
    r"equalized odds",
    r"equal opportunity",
    r"disparate impact",
    r"toxicity score",
    r"stereotype score",
    r"refusal rate",
    r"fairness metric",
    r"bias audit",
]

Q3_OPERATIONALIZATION_PATTERNS = [
    r"\bbbq\b",
    r"\bbold\b",
    r"stereoset",
    r"crows?-pairs",
    r"realtoxicityprompts",
    r"helm",
    r"decodingtrust",
    r"truthfulqa",
    r"mmlu",
    r"red teaming",
    r"prompting",
    r"prompt audit",
    r"alignment",
    r"mitigation",
    r"constitutional",
    r"rlhf",
    r"safety policy",
    r"benchmark",
    r"dataset",
]

Q3_EXCLUDE_PATTERNS = [
    r"\bshap\b",
    r"\blime\b",
    r"grad-?cam",
    r"integrated gradients?",
    r"saliency",
    r"attention visualization",
    r"feature attribution",
]

Q4_IMPACT_PATTERNS = [
    r"\bbbq\b",
    r"\bbold\b",
    r"stereoset",
    r"crows?-pairs",
    r"realtoxicityprompts",
    r"toxicity score",
    r"stereotype score",
    r"refusal rate",
    r"bias benchmark",
    r"fairness metric",
    r"demographic parity",
    r"equalized odds",
    r"equal opportunity",
    r"disparate impact",
    r"auditing",
]

Q4_EXCLUDE_PATTERNS = [
    r"\bshap\b",
    r"\blime\b",
    r"grad-?cam",
    r"integrated gradients?",
    r"saliency",
    r"attention visualization",
    r"feature attribution",
]

Q6_GENERATION_PATTERNS = [
    r"chain[- ]of[- ]thought",
    r"\bcot\b",
    r"rationale generation",
    r"self-?explanation",
    r"llm[- ]as[- ]a[- ]judge",
    r"judge model",
    r"\brag\b",
    r"retrieval-augmented generation",
    r"natural language explanation",
    r"explanation generation",
    r"narrative",
    r"summar",
    r"translate",
    r"chatbot",
    r"conversational",
]

Q6_EXCLUDE_PATTERNS = [
    r"\bshap\b",
    r"\blime\b",
    r"grad-?cam",
    r"integrated gradients?",
    r"saliency",
    r"attention visualization",
    r"feature attribution",
    r"\btcav\b",
    r"activation patching",
    r"probing",
    r"mechanistic interpret",
]

TECHNIQUE_TYPE_SHORT = {
    "explanation_method": "Explain",
    "interpretability_or_probing_method": "Inspect",
    "fairness_evaluation_method": "Fairness eval",
    "bias_or_toxicity_evaluation_method": "Bias eval",
    "benchmark_or_dataset": "Benchmark",
    "alignment_or_mitigation_method": "Mitigation",
    "prompting_or_red_teaming_protocol": "Prompting",
    "model_or_system_component": "Model",
    "statistical_analysis": "Metric",
    "metric": "Metric",
    "human_evaluation_protocol": "Human eval",
    "qualitative_or_taxonomy_method": "Qualitative",
    "other_specific_method": "Method",
}

CANONICAL_TECHNIQUE_RULES = [
    (r"\bshap(?:ley)?\b|shapley additive", "SHAP"),
    (r"\blime\b|local interpretable model-agnostic", "LIME"),
    (r"grad-?cam\+\+", "Grad-CAM++"),
    (r"grad-?cam", "Grad-CAM"),
    (r"integrated gradients?", "Integrated Gradients"),
    (r"\btcav\b|concept activation", "TCAV"),
    (r"attention visualization", "Attention Visualization"),
    (r"attention (?:weights?|maps?)", "Attention Analysis"),
    (r"feature attribution", "Feature Attribution"),
    (r"activation patching", "Activation Patching"),
    (r"counterfactual", "Counterfactual Explanations"),
    (r"chain[- ]of[- ]thought|\bcot\b", "Chain-of-Thought"),
    (r"rationale generation", "Rationale Generation"),
    (r"self-?explanation", "Self-Explanation"),
    (r"llm[- ]as[- ]a[- ]judge|judge model", "LLM-as-a-Judge"),
    (r"retrieval-augmented generation|\brag\b", "RAG"),
    (r"\bbbq\b", "BBQ"),
    (r"\bbold\b", "BOLD"),
    (r"stereoset", "StereoSet"),
    (r"crows?-pairs", "CrowS-Pairs"),
    (r"realtoxicityprompts|real toxicity prompts", "RealToxicityPrompts"),
    (r"\bhelm\b", "HELM"),
    (r"decodingtrust", "DecodingTrust"),
    (r"truthfulqa", "TruthfulQA"),
    (r"\bmmlu\b", "MMLU"),
    (r"demographic parity(?: difference| gap)?", "Demographic Parity"),
    (r"equalized odds(?: difference| gap)?", "Equalized Odds"),
    (r"equal opportunity(?: difference| gap)?", "Equal Opportunity"),
    (r"disparate impact", "Disparate Impact"),
    (r"toxicity score", "Toxicity Score"),
    (r"stereotype score", "Stereotype Score"),
    (r"refusal rate", "Refusal Rate"),
    (r"federated learning", "Federated Learning"),
    (r"xgboost", "XGBoost"),
]


def wrap(text: str, width: int) -> str:
    return "\n".join(textwrap.wrap(str(text), width=width, break_long_words=False))


def evidence_tier(count: int, max_count: int) -> int:
    if max_count <= 0:
        return 1
    return max(1, min(5, math.ceil(5 * count / max_count)))


def load_goal_stats(path: Path) -> Dict[str, Dict[str, float]]:
    if not path.exists():
        raise FileNotFoundError(f"Could not find: {path}")

    df = pd.read_csv(path)
    if "question_id" not in df.columns or "relevant" not in df.columns:
        raise ValueError("Master CSV must contain 'question_id' and 'relevant' columns.")

    rel = df[df["relevant"] == True].copy()
    total = int(len(rel))
    if total == 0:
        raise ValueError("No relevant assignments found in the master CSV.")

    goal_stats: Dict[str, Dict[str, float]] = {}
    for q, meta in GOAL_INFO.items():
        count = int((rel["question_id"] == q).sum())
        goal_stats[q] = {
            "assignments": count,
            "percent": (100.0 * count / total) if total else 0.0,
            "axis": str(meta["axis"]),
        }

    axis_stats: Dict[str, Dict[str, float]] = {}
    for axis_name in AXES:
        axis_total = sum(int(goal_stats[q]["assignments"]) for q, meta in GOAL_INFO.items() if meta["axis"] == axis_name)
        axis_stats[axis_name] = {
            "assignments": axis_total,
            "percent": (100.0 * axis_total / total) if total else 0.0,
        }

    return {"goals": goal_stats, "axes": axis_stats, "total": {"assignments": total}}


def load_top_techniques(path: Path, top_k: int) -> Dict[str, pd.DataFrame]:
    if not path.exists():
        raise FileNotFoundError(f"Could not find: {path}")

    clean_assignments_path = path.parent / "technique_assignments_clean.csv"
    if clean_assignments_path.exists():
        df = build_goal_summary_from_assignments(clean_assignments_path)
    else:
        df = pd.read_csv(path)
        required = {"q", "technique", "papers"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Missing columns in {path}: {missing}")
        df = prepare_summary_from_summary_csv(df)

    df = assign_exclusive_goal_per_technique(df)

    result = {}
    for q in GOAL_INFO:
        part = df[df["q"] == q].copy()
        if part.empty:
            result[q] = pd.DataFrame(columns=df.columns)
            continue

        part["technique"] = part["technique"].map(clean_technique_name)
        part = filter_goal_techniques(q, part)
        part = part.drop_duplicates(subset=["technique"], keep="first")
        part = part.sort_values(["papers", "technique"], ascending=[False, True]).head(top_k).copy()
        max_count = int(part["papers"].max()) if not part.empty else 1
        if "tier_within_goal" not in part.columns:
            part["tier_within_goal"] = part["papers"].apply(lambda x: evidence_tier(int(x), max_count))
        result[q] = part

    return result


def prepare_summary_from_summary_csv(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["technique"] = work["technique"].map(clean_technique_name)
    work["technique_type"] = work["technique_type"].map(normalize_technique_type)
    if "examples" not in work.columns:
        work["examples"] = ""
    if "evidence_examples" not in work.columns:
        work["evidence_examples"] = ""

    grouped_rows = []
    for (q, technique), part in work.groupby(["q", "technique"], sort=False):
        type_counts = Counter(part["technique_type"].astype(str).tolist())
        technique_type = type_counts.most_common(1)[0][0] if type_counts else "other_specific_method"
        grouped_rows.append(
            {
                "q": q,
                "technique": technique,
                "technique_type": technique_type,
                "papers": int(part["papers"].sum()),
                "examples": " || ".join(list(dict.fromkeys(part["examples"].dropna().astype(str)))[:3]),
                "evidence_examples": " || ".join(list(dict.fromkeys(part["evidence_examples"].dropna().astype(str)))[:3]),
            }
        )

    return pd.DataFrame(grouped_rows)


def clean_technique_name(value: object) -> str:
    text = str(value).strip()
    text = text.replace("SHapley Additive exPlanations", "SHAP")
    text = text.replace("SHapley additive explanations", "SHAP")
    text = text.replace("Explainable AI (XAI", "XAI")
    text = text.replace("Large Language Models (LLMs", "LLMs")
    text = text.replace("Large Language Model (LLM", "LLM")
    text = text.replace("SHAP (SHapley Additive exPlanations", "SHAP")
    text = text.replace("SHAP (SHapley Additive Explanations", "SHAP")
    text = text.replace("(", " (")
    text = re.sub(r"\s+", " ", text).strip(" ,;:")
    if text.count("(") > text.count(")"):
        text = text.rstrip("(").strip()
    text = text.replace("  ", " ")
    lowered = text.lower()
    for pattern, canonical in CANONICAL_TECHNIQUE_RULES:
        if re.search(pattern, lowered):
            return canonical
    return text


def normalize_technique_type(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return "other_specific_method"
    return text


def build_goal_summary_from_assignments(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"paper_id", "q", "technique"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in {path}: {missing}")

    df["technique"] = df["technique"].map(clean_technique_name)
    df["technique_type"] = df["technique_type"].map(normalize_technique_type)
    df = df[df["technique"].map(is_useful_technique)].copy()
    df = df.drop_duplicates(subset=["paper_id", "q", "technique"])

    grouped_rows = []
    for (q, technique), part in df.groupby(["q", "technique"], sort=False):
        type_counts = Counter(part["technique_type"].astype(str).tolist())
        technique_type = type_counts.most_common(1)[0][0] if type_counts else "other_specific_method"
        grouped_rows.append(
            {
                "q": q,
                "technique": technique,
                "technique_type": technique_type,
                "papers": int(part["paper_id"].nunique()),
                "examples": " || ".join(list(dict.fromkeys(part["title"].dropna().astype(str)))[:3]) if "title" in part.columns else "",
                "evidence_examples": " || ".join(list(dict.fromkeys(part["evidence_phrase"].dropna().astype(str)))[:3]) if "evidence_phrase" in part.columns else "",
            }
        )

    out = pd.DataFrame(grouped_rows)
    if out.empty:
        return pd.DataFrame(columns=["q", "technique", "technique_type", "papers", "examples", "evidence_examples", "tier_within_goal"])

    return recompute_tiers(out)


def recompute_tiers(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if out.empty:
        out["tier_within_goal"] = []
        return out

    tier_map: Dict[tuple[str, str], int] = {}
    for q, part in out.groupby("q", sort=False):
        max_count = int(part["papers"].max()) if not part.empty else 1
        for _, row in part.iterrows():
            tier_map[(str(row["q"]), str(row["technique"]))] = evidence_tier(int(row["papers"]), max_count)

    out["tier_within_goal"] = out.apply(
        lambda row: tier_map.get((str(row["q"]), str(row["technique"])), 1),
        axis=1,
    )
    return out


def assign_exclusive_goal_per_technique(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    candidates = []
    for q in GOAL_INFO:
        part = df[df["q"] == q].copy()
        if part.empty:
            continue
        part = part[part["technique"].map(is_useful_technique)].copy()
        part = filter_goal_techniques(q, part)
        if part.empty:
            continue
        candidates.append(part)

    if not candidates:
        return pd.DataFrame(columns=df.columns)

    candidate_df = pd.concat(candidates, ignore_index=True)
    candidate_df = recompute_tiers(candidate_df)
    candidate_df["goal_priority"] = candidate_df["q"].map({q: i for i, q in enumerate(GOAL_INFO.keys())})

    chosen_rows = []
    for technique, part in candidate_df.groupby("technique", sort=False):
        ranked = part.sort_values(
            ["tier_within_goal", "papers", "goal_priority"],
            ascending=[False, False, True],
        )
        chosen_rows.append(ranked.iloc[0].to_dict())

    out = pd.DataFrame(chosen_rows).drop(columns=["goal_priority"], errors="ignore")
    out = recompute_tiers(out)
    return out


def is_useful_technique(name: str) -> bool:
    lowered = name.lower().strip()
    if lowered in GENERIC_TECHNIQUE_NAMES:
        return False
    for pattern in GENERIC_TECHNIQUE_PATTERNS:
        if re.search(pattern, lowered):
            return False
    if len(lowered) < 3:
        return False
    return True


def _combined_goal_text(row: pd.Series) -> str:
    return " ".join(
        [
            str(row.get("technique", "")),
            str(row.get("technique_type", "")),
            str(row.get("evidence_examples", "")),
            str(row.get("examples", "")),
        ]
    ).lower()


def _matches_any(patterns: list[str], text: str) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def technique_fits_goal(q: str, row: pd.Series) -> bool:
    name = str(row.get("technique", ""))
    if not is_useful_technique(name):
        return False

    text = _combined_goal_text(row)

    if q == "Q1":
        if _matches_any(Q1_EXCLUDE_PATTERNS, text):
            return False
        return _matches_any(Q1_JUSTIFICATION_PATTERNS, text)

    if q == "Q2":
        return _matches_any(Q2_DIAGNOSIS_PATTERNS, text)

    if q == "Q3":
        if _matches_any(Q3_EXCLUDE_PATTERNS, text):
            return False
        return _matches_any(Q3_OPERATIONALIZATION_PATTERNS, text)

    if q == "Q4":
        if _matches_any(Q4_EXCLUDE_PATTERNS, text):
            return False
        return _matches_any(Q4_IMPACT_PATTERNS, text)

    if q == "Q5":
        return _matches_any(Q5_INSPECTION_PATTERNS, text)

    if q == "Q6":
        if _matches_any(Q6_EXCLUDE_PATTERNS, text):
            return False
        return _matches_any(Q6_GENERATION_PATTERNS, text)

    return True


def fallback_goal_filter(q: str, part: pd.DataFrame) -> pd.DataFrame:
    part = part[part["technique"].map(is_useful_technique)].copy()

    # Keep Q6 generation from collapsing back into pure inspection methods.
    if q == "Q6":
        mask = ~part.apply(lambda row: _matches_any(Q6_EXCLUDE_PATTERNS, _combined_goal_text(row)), axis=1)
        softened = part[mask].copy()
        if not softened.empty:
            return softened

    # Keep Q3/Q4 free from obvious inspection-only explanation methods if we can.
    if q in {"Q3", "Q4"}:
        exclude_patterns = Q3_EXCLUDE_PATTERNS if q == "Q3" else Q4_EXCLUDE_PATTERNS
        mask = ~part.apply(lambda row: _matches_any(exclude_patterns, _combined_goal_text(row)), axis=1)
        softened = part[mask].copy()
        if not softened.empty:
            return softened

    return part


def filter_goal_techniques(q: str, part: pd.DataFrame) -> pd.DataFrame:
    strict = part[part.apply(lambda row: technique_fits_goal(q, row), axis=1)].copy()
    if not strict.empty:
        return strict
    return fallback_goal_filter(q, part)


def add_round_box(ax, x, y, w, h, facecolor, edgecolor, linewidth=1.5, radius=0.02, alpha=1.0):
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle=f"round,pad=0.008,rounding_size={radius}",
        linewidth=linewidth,
        edgecolor=edgecolor,
        facecolor=facecolor,
        alpha=alpha,
    )
    ax.add_patch(patch)
    return patch


def add_text(ax, x, y, text, size=10, weight="normal", color="#111827", ha="left", va="top", alpha=1.0):
    ax.text(
        x,
        y,
        text,
        fontsize=size,
        fontweight=weight,
        color=color,
        ha=ha,
        va=va,
        alpha=alpha,
        family="DejaVu Sans",
    )


def draw_axis_header(ax, x, y, w, axis_name: str, axis_stats: Dict[str, float]):
    meta = AXES[axis_name]
    add_round_box(ax, x, y, w, 0.09, facecolor="white", edgecolor=meta["color"], linewidth=1.6, radius=0.018)
    ax.add_patch(Rectangle((x, y + 0.058), w, 0.032, color=meta["color"]))
    add_text(ax, x + w / 2, y + 0.084, axis_name, size=15, weight="bold", color="white", ha="center", va="top")
    add_text(ax, x + w / 2, y + 0.044, meta["subtitle"], size=10, weight="bold", color="#111827", ha="center", va="top")
    add_text(
        ax,
        x + w / 2,
        y + 0.018,
        f'{int(axis_stats["assignments"])} assignments  |  {axis_stats["percent"]:.1f}%',
        size=8.5,
        color="#4B5563",
        ha="center",
        va="top",
    )


def draw_goal_box(ax, x, y, w, h, q: str, goal_stats: Dict[str, float], max_goal_assignments: int):
    info = GOAL_INFO[q]
    axis_name = str(info["axis"])
    axis_color = AXES[axis_name]["color"]
    light = AXES[axis_name]["light"]

    add_round_box(ax, x, y, w, h, facecolor=light, edgecolor=axis_color, linewidth=1.6, radius=0.012)

    header_h = 0.055
    ax.add_patch(Rectangle((x, y + h - header_h), w, header_h, color=axis_color))

    add_text(ax, x + 0.012, y + h - 0.012, str(info["abbr"]), size=18, weight="bold", color="white", va="top")
    tier = evidence_tier(int(goal_stats["assignments"]), max_goal_assignments)
    add_text(ax, x + w - 0.012, y + h - 0.012, f"+{tier}", size=13, weight="bold", color="white", ha="right", va="top")
    add_text(ax, x + 0.012, y + h - header_h - 0.010, str(info["goal"]), size=12, weight="bold", color="#111827", alpha=0.98, va="top")

    body_y = y + h - header_h - 0.038
    add_text(ax, x + 0.012, body_y, str(info["direction"]), size=8.2, weight="bold", color="#374151")

    role = str(info["role"])
    add_round_box(ax, x + 0.012, body_y - 0.062, 0.10, 0.024, facecolor="white", edgecolor=ROLE_COLORS[role], linewidth=1.0, radius=0.008)
    add_text(ax, x + 0.062, body_y - 0.047, role, size=7.2, weight="bold", color=ROLE_COLORS[role], ha="center", va="center")
    add_text(
        ax,
        x + w - 0.012,
        body_y - 0.044,
        f'{int(goal_stats["assignments"])} assign. | {goal_stats["percent"]:.1f}%',
        size=7.2,
        color="#4B5563",
        ha="right",
    )
    add_text(ax, x + 0.012, body_y - 0.080, wrap(str(info["meaning"]), 34), size=7.1, color="#111827")


def draw_technique_box(ax, x, y, w, h, row, axis_name: str):
    color = AXES[axis_name]["color"]
    add_round_box(ax, x, y, w, h, facecolor="white", edgecolor="#D5D9E0", linewidth=0.9, radius=0.010, alpha=1.0)
    ax.add_patch(Rectangle((x, y + h - 0.012), w, 0.012, color=color, alpha=0.9))

    technique = str(row["technique"])
    papers = int(row["papers"])
    tier = int(row.get("tier_within_goal", 1))
    technique_type = str(row.get("technique_type", "")).replace("_", " ")
    technique_type = TECHNIQUE_TYPE_SHORT.get(technique_type, TECHNIQUE_TYPE_SHORT.get(str(row.get("technique_type", "")), "Method"))

    add_text(ax, x + 0.010, y + h - 0.018, wrap(technique, 26), size=7.4, weight="bold", color="#111827", va="top")
    add_text(ax, x + w - 0.010, y + h - 0.018, f"+{tier}", size=8.2, weight="bold", color=color, ha="right", va="top")
    add_text(ax, x + 0.010, y + 0.013, f"{papers} papers", size=6.6, color="#4B5563", va="bottom")
    add_text(ax, x + w - 0.010, y + 0.013, technique_type, size=6.2, color="#6B7280", ha="right", va="bottom")


def build_selected_rows(top: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for q, part in top.items():
        info = GOAL_INFO[q]
        if part.empty:
            rows.append(
                {
                    "q": q,
                    "axis": info["axis"],
                    "goal": info["goal"],
                    "direction": info["direction"],
                    "role": info["role"],
                    "technique": "",
                    "technique_type": "",
                    "papers": 0,
                    "tier_within_goal": 0,
                    "selected_for_figure": False,
                    "note": "No specific recurrent technique extracted",
                }
            )
            continue

        for _, row in part.iterrows():
            rows.append(
                {
                    "q": q,
                    "axis": info["axis"],
                    "goal": info["goal"],
                    "direction": info["direction"],
                    "role": info["role"],
                    "technique": str(row.get("technique", "")),
                    "technique_type": str(row.get("technique_type", "")),
                    "papers": int(row.get("papers", 0)),
                    "tier_within_goal": int(row.get("tier_within_goal", 0)),
                    "selected_for_figure": True,
                    "note": "",
                }
            )
    return pd.DataFrame(rows)


def print_selected_techniques(top: Dict[str, pd.DataFrame]) -> None:
    print("\n=== Selected Techniques For Figure ===", flush=True)
    for q in GOAL_INFO:
        info = GOAL_INFO[q]
        print(f"{q} | {info['goal']} | {info['direction']}", flush=True)
        part = top.get(q, pd.DataFrame())
        if part is None or part.empty:
            print("  - No specific recurrent technique extracted", flush=True)
            continue
        for _, row in part.iterrows():
            technique = str(row.get("technique", "")).strip()
            papers = int(row.get("papers", 0))
            tier = int(row.get("tier_within_goal", 0))
            ttype = TECHNIQUE_TYPE_SHORT.get(str(row.get("technique_type", "")), str(row.get("technique_type", "")))
            print(f"  - {technique} | {papers} papers | +{tier} | {ttype}", flush=True)
    print("", flush=True)


def write_selected_sidecars(output_base: Path, selected_df: pd.DataFrame) -> None:
    csv_path = output_base.parent / f"{output_base.stem}_selected_techniques.csv"
    md_path = output_base.parent / f"{output_base.stem}_selected_techniques.md"
    selected_df.to_csv(csv_path, index=False)

    with md_path.open("w", encoding="utf-8") as f:
        f.write("# FAIR-LENS Figure Techniques\n\n")
        for q in GOAL_INFO:
            info = GOAL_INFO[q]
            f.write(f"## {q} - {info['goal']}\n\n")
            part = selected_df[(selected_df["q"] == q) & (selected_df["selected_for_figure"] == True)].copy()
            if part.empty:
                f.write("- No specific recurrent technique extracted\n\n")
                continue
            for _, row in part.iterrows():
                f.write(
                    f"- **{row['technique']}** | {int(row['papers'])} papers | +{int(row['tier_within_goal'])} | {row['technique_type']}\n"
                )
            f.write("\n")

    print(f"Saved: {csv_path}", flush=True)
    print(f"Saved: {md_path}", flush=True)


def make_figure(summary_path: Path, output_base: Path, top_k: int, master_path: Path):
    top = load_top_techniques(summary_path, top_k=top_k)
    stats = load_goal_stats(master_path)
    goal_stats = stats["goals"]
    axis_stats = stats["axes"]
    max_goal_assignments = max(int(goal_stats[q]["assignments"]) for q in GOAL_INFO)
    selected_df = build_selected_rows(top)
    print_selected_techniques(top)
    write_selected_sidecars(output_base, selected_df)

    max_selected = max((len(part) for part in top.values()), default=0)
    extra_rows = max(0, max_selected - 3)
    fig_height = min(24.0, 12.5 + extra_rows * 1.35)
    tech_h = max(0.034, 0.058 - extra_rows * 0.0022)
    tech_gap = max(0.004, 0.008 - extra_rows * 0.0004)
    goal_h = 0.145

    fig = plt.figure(figsize=(15, fig_height), dpi=220)
    ax = plt.gca()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    fig.patch.set_facecolor("#F7F8FC")
    add_text(ax, 0.5, 0.978, "FAIR-LENS Evidence Table", size=22, weight="bold", color="#111827", ha="center", va="top")
    add_text(
        ax,
        0.5,
        0.948,
        "Three axes, two roles, six directional goals, and recurrent techniques extracted from the reviewed corpus",
        size=11.2,
        color="#4B5563",
        ha="center",
        va="top",
    )

    col_w = 0.305
    col_xs = {
        "Accountability": 0.02,
        "Alignment": 0.3475,
        "Visibility": 0.675,
    }

    header_y = 0.865
    gap_goal = 0.026

    goal_order = {
        "Accountability": ["Q1", "Q2"],
        "Alignment": ["Q3", "Q4"],
        "Visibility": ["Q5", "Q6"],
    }

    for axis_name, x in col_xs.items():
        draw_axis_header(ax, x, header_y, col_w, axis_name, axis_stats[axis_name])
        y = 0.695
        for q in goal_order[axis_name]:
            draw_goal_box(ax, x, y, col_w, goal_h, q, goal_stats[q], max_goal_assignments)
            techniques = top.get(q, pd.DataFrame())
            ty = y - tech_gap - tech_h
            if techniques.empty:
                add_round_box(ax, x, ty, col_w, tech_h, facecolor="white", edgecolor="#D1D5DB", linewidth=0.8, radius=0.010)
                add_text(ax, x + 0.010, ty + tech_h - 0.012, "No specific recurrent technique extracted", size=7.2, color="#6B7280", va="top")
                ty -= tech_h + tech_gap
            else:
                for _, row in techniques.iterrows():
                    draw_technique_box(ax, x, ty, col_w, tech_h, row, axis_name)
                    ty -= tech_h + tech_gap
            y = ty - gap_goal

    footer = (
        "Evidence tier: +1 to +5. For goal boxes, tiers are calculated from assignment volume relative to the largest goal. "
        "For technique boxes, tiers are calculated within each FAIR-LENS goal from the number of papers using the technique. "
        "The tier indicates evidence volume, not methodological quality or normative importance."
    )
    add_text(ax, 0.02, 0.022, wrap(footer, 150), size=8.0, color="#4B5563", va="bottom")

    output_base.parent.mkdir(parents=True, exist_ok=True)
    png_path = output_base.with_suffix(".png")
    pdf_path = output_base.with_suffix(".pdf")
    plt.savefig(png_path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.savefig(pdf_path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)

    print(f"Saved: {png_path}", flush=True)
    print(f"Saved: {pdf_path}", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--summary",
        default="outputs/fairlens_techniques/technique_summary_by_goal.csv",
        help="Technique summary CSV created by extract_techniques.py",
    )
    parser.add_argument(
        "--output",
        default="outputs/figures/fairlens_evidence_table_enriched",
        help="Output path without extension.",
    )
    parser.add_argument(
        "--top_k",
        type=int,
        default=3,
        help="Number of technique boxes to show under each goal.",
    )
    parser.add_argument(
        "--master",
        default="outputs/tri_results_master.csv",
        help="Master FAIR-LENS assignment CSV used to compute dynamic counts.",
    )
    args = parser.parse_args()

    make_figure(
        summary_path=Path(args.summary),
        output_base=Path(args.output),
        top_k=args.top_k,
        master_path=Path(args.master),
    )


if __name__ == "__main__":
    main()
