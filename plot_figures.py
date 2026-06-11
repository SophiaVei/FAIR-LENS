#!/usr/bin/env python3
"""
plot_figures.py
Publication-quality figures for the FAIR-LENS systematic review.
Reads outputs/tri_results_master.csv and writes transparent PNGs + PDFs
to outputs/figures/ (fig1–fig23, aligned with the dashboard where noted).

Usage:
    python plot_figures.py
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.dates as mdates
from pathlib import Path
import numpy as np
import re

# ── Paths ────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
INPUT_CSV  = SCRIPT_DIR / "outputs" / "tri_results_master.csv"
OUTPUT_DIR = SCRIPT_DIR / "outputs" / "figures"

# ── Question metadata (matches questions.py exactly) ─────────────────
Q_META = {
    "Q1": {"short": "Q1: F\u2192E",  "label": "Fairness \u2192 Explainability",     "cluster": "F\u2194E"},
    "Q2": {"short": "Q2: E\u2192F",  "label": "Explainability \u2192 Fairness",     "cluster": "F\u2194E"},
    "Q3": {"short": "Q3: F\u2192L",  "label": "Fairness \u2192 LLMs",              "cluster": "F\u2194L"},
    "Q4": {"short": "Q4: L\u2192F",  "label": "LLMs \u2192 Fairness",              "cluster": "F\u2194L"},
    "Q5": {"short": "Q5: E\u2192L",  "label": "Explainability \u2192 LLMs",         "cluster": "E\u2194L"},
    "Q6": {"short": "Q6: L\u2192E",  "label": "LLMs \u2192 Explainability",         "cluster": "E\u2194L"},
}
Q_ORDER = ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6"]

# ── Color palette (matches the dashboard UI) ─────────────────────────
# Per-question colors (used in bar charts, pie charts)
Q_COLORS = {
    "Q1": "#f4a261",   # warm orange
    "Q2": "#f9844a",   # coral
    "Q3": "#f9c74f",   # gold
    "Q4": "#90be6d",   # lime green
    "Q5": "#43aa8b",   # teal
    "Q6": "#577590",   # steel blue
}

# Pillar colors (dashboard: mentions, thematic radar, topical coverage)
PILLAR_COLORS = {
    "Fairness":       "#f4a261",
    "Explainability": "#a3b18a",
    "LLMs":           "#8ecae6",
}

# Pairwise co-mention colors (dashboard: co-mention intensity)
PAIR_COLORS = {
    "Fairness \u2194 Explainability": "#f9c74f",
    "Fairness \u2194 LLMs":           "#f9844a",
    "Explainability \u2194 LLMs":     "#90be6d",
}

# Edge/cluster colors (triangle edges, research clusters)
EDGE_COLORS = {
    "F\u2194E": "#f4a261",
    "F\u2194L": "#1d4e89",
    "E\u2194L": "#2a7f3f",
}

FOCUS_COLORS = {
    "Proactive (Design)": "#f4a261",
    "Diagnostic (Audit)": "#577590",
}

METHODOLOGY_COLORS = {
    "framework":   "#f4a261",
    "dataset":     "#219ebc",
    "experiment":  "#8ecae6",
    "mitigation":  "#ffb703",
    "audit":       "#577590",
    "benchmark":   "#43aa8b",
    "survey":      "#90be6d",
}

MODEL_FAMILY_COLORS = {
    "gpt":   "#8ecae6",
    "llama": "#ffb703",
    "bert":  "#fb8500",
}

MATURITY_LINE_COLORS = {
    "accessibility": "#8ecae6",
    "depth":         "#f4a261",
}

CADENCE_COLOR = "#8ecae6"
SYNERGY_RADAR_COLOR = "#6366f1"

# One color per "directions covered" count (1–6); ramp reuses Q palette low→high integration
DIRECTION_COUNT_COLORS = {i: Q_COLORS[q] for i, q in zip(range(1, 7), reversed(Q_ORDER))}

DISCIPLINE_PALETTE = ["#8ecae6", "#219ebc", "#023047", "#ffb703", "#fb8500", "#90be6d", "#43aa8b"]
CLUSTER_PALETTE = DISCIPLINE_PALETTE
TAXONOMY_BAR_PALETTE = ["#f4a261", "#f9844a", "#f9c74f", "#90be6d", "#43aa8b", "#577590", "#8ecae6"]
KEYWORD_PALETTE = TAXONOMY_BAR_PALETTE

TAXONOMY = {
    "Domains": ["medical", "clinical", "healthcare", "finance", "legal", "education",
                "hiring", "recruitment", "justice", "security", "software", "scientific"],
    "XAI Methods": ["shap", "lime", "attention", "saliency", "integrated gradients", "counterfactual",
                    "rationale", "probing", "mechanistic", "feature attribution", "attribution"],
    "Fairness Concepts": ["gender", "race", "ethnic", "age", "multilingual", "language", "geographic",
                          "socioeconomic", "stereotyp", "toxicity", "bias", "parity", "equality"],
    "Models": ["gpt", "llama", "bert", "roberta", "mistral", "claude", "gemini", "t5", "palm",
               "transformer", "bloom"],
    "Paper Type": ["benchmark", "dataset", "mitigation", "audit", "survey", "human study",
                   "experiment", "framework"],
}

VENUE_MAP = {
    "NLP": ["acl", "emnlp", "naacl", "tacl", "coling", "lrec"],
    "HCI/Social": ["chi", "cscw", "uist", "tochi", "human-computer"],
    "Fairness/Ethics": ["facct", "aies", "ethics", "equity", "responsible"],
    "General AI/ML": ["neurips", "iclr", "icml", "aaai", "ijcai", "kdd", "cvpr", "iccv"],
    "Application": ["medical", "health", "legal", "law", "finance", "education", "software", "scientific"],
}

METHODOLOGY_TYPES = ["framework", "dataset", "experiment", "mitigation", "audit", "benchmark", "survey"]

TITLE_STOP_WORDS = frozenset({
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "from",
    "as", "is", "was", "are", "were", "been", "be", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "must", "can", "this", "that", "these", "those", "i",
    "you", "he", "she", "it", "we", "they", "what", "which", "who", "when", "where", "why", "how",
    "all", "each", "every", "both", "few", "more", "most", "other", "some", "such", "no", "nor", "not",
    "only", "own", "same", "so", "than", "too", "very", "via", "using", "based",
})

# Publication: transparent canvas, dark ink readable on white paper
BG_TRANSPARENT = "none"
TEXT_MAIN  = "#111827"
TEXT_MUTED = "#4b5563"
GRID_COLOR = "#d1d5db"
POLAR_GRID_COLOR = "#374151"
POLAR_SPINE_COLOR = "#111827"
POLAR_GRID_LW = 1.25
POLAR_SPINE_LW = 2.0


# ═══════════════════════════════════════════════════════════════════════
# Style setup
# ═══════════════════════════════════════════════════════════════════════
def setup_style():
    """Configure matplotlib for publication-quality, light-themed, transparent output."""
    plt.rcParams.update({
        # Figure
        "figure.facecolor":    "none",
        "figure.edgecolor":    "none",
        "figure.dpi":          150,
        "savefig.dpi":         300,
        "savefig.bbox":        "tight",
        "savefig.pad_inches":  0.3,
        "savefig.facecolor":   "none",
        # Axes
        "axes.facecolor":      "none",
        "axes.edgecolor":      TEXT_MAIN,
        "axes.labelcolor":     TEXT_MAIN,
        "axes.titlesize":      12,
        "axes.labelsize":      11,
        "axes.grid":           True,
        "axes.spines.top":     False,
        "axes.spines.right":   False,
        # Grid
        "grid.color":          GRID_COLOR,
        "grid.linewidth":      0.6,
        "grid.alpha":          0.9,
        # Ticks
        "xtick.color":         TEXT_MAIN,
        "ytick.color":         TEXT_MAIN,
        "xtick.labelsize":     10,
        "ytick.labelsize":     10,
        # Text
        "text.color":          TEXT_MAIN,
        "font.family":         "sans-serif",
        "font.sans-serif":     ["Inter", "Segoe UI", "Helvetica Neue", "Arial"],
        "font.size":           11,
        # Legend
        "legend.facecolor":    "none",
        "legend.edgecolor":    "#d1d5db",
        "legend.fontsize":     9,
        "legend.framealpha":   0.0,
    })


def _transparent_figure(fig):
    """Ensure figure and axes backgrounds stay transparent for export."""
    fig.patch.set_facecolor(BG_TRANSPARENT)
    fig.patch.set_alpha(0)
    for ax in fig.axes:
        ax.set_facecolor(BG_TRANSPARENT)
        if hasattr(ax, "patch"):
            ax.patch.set_alpha(0)


def _style_legend(leg):
    """Legends readable on transparent export."""
    if leg is None:
        return
    frame = leg.get_frame()
    frame.set_facecolor(BG_TRANSPARENT)
    frame.set_edgecolor(TEXT_MUTED)
    frame.set_alpha(0.0)
    for text in leg.get_texts():
        text.set_color(TEXT_MAIN)


def _style_polar_axes(ax):
    """Stronger polar grid and spokes for publication on transparent background."""
    ax.set_facecolor(BG_TRANSPARENT)
    ax.grid(
        True,
        color=POLAR_GRID_COLOR,
        linestyle="-",
        linewidth=POLAR_GRID_LW,
        alpha=1.0,
    )
    ax.spines["polar"].set_visible(True)
    ax.spines["polar"].set_color(POLAR_SPINE_COLOR)
    ax.spines["polar"].set_linewidth(POLAR_SPINE_LW)
    ax.tick_params(axis="both", colors=TEXT_MAIN, grid_color=POLAR_GRID_COLOR)


def save(fig, name: str):
    """Save figure as both PNG and PDF with transparency."""
    _transparent_figure(fig)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    kwargs = dict(transparent=True, facecolor="none", edgecolor="none")
    fig.savefig(OUTPUT_DIR / f"{name}.png", **kwargs)
    fig.savefig(OUTPUT_DIR / f"{name}.pdf", **kwargs)
    print(f"  [OK] {name}.png / .pdf")
    plt.close(fig)


# ═══════════════════════════════════════════════════════════════════════
# Data loading
# ═══════════════════════════════════════════════════════════════════════
def load_data():
    df = pd.read_csv(INPUT_CSV)
    # Keep only relevant rows
    rel = df[df["relevant"] == True].copy()
    rel["year"] = pd.to_numeric(rel["year"], errors="coerce")
    return df, rel


def unique_papers(rel: pd.DataFrame) -> pd.DataFrame:
    return rel.drop_duplicates(subset=["title"])


def infer_partial_year_cutoff(papers: pd.DataFrame) -> pd.Timestamp | None:
    """
    Infer a defensible cutoff for the partial final year from publisher URL timestamps.

    We only use exact-ish signals already present in the local data, currently the
    `version=<unix_timestamp>` pattern seen in some publisher PDF URLs. If found for
    the final year, we advance to the next month boundary so the x-axis ends at the
    last covered month rather than implying the whole year is observed.
    """
    if papers.empty or "year" not in papers.columns:
        return None

    max_year = pd.to_numeric(papers["year"], errors="coerce").dropna()
    if max_year.empty:
        return None
    max_year = int(max_year.max())

    exact_dates: list[pd.Timestamp] = []
    year_mask = pd.to_numeric(papers["year"], errors="coerce") == max_year
    for url in papers.loc[year_mask, "url"].fillna("").astype(str):
        match = re.search(r"[?&]version=(\d{10})\b", url)
        if not match:
            continue
        try:
            ts = pd.to_datetime(int(match.group(1)), unit="s", utc=True).tz_localize(None)
        except (ValueError, TypeError, OverflowError):
            continue
        exact_dates.append(ts)

    if not exact_dates:
        return None

    latest_exact = max(exact_dates)
    if latest_exact.year != max_year:
        return None

    return latest_exact.normalize() + pd.offsets.MonthBegin(1)


def extract_keywords(text: str) -> dict[str, list[str]]:
    text = str(text).lower()
    found = {cat: [] for cat in TAXONOMY}
    for cat, keywords in TAXONOMY.items():
        for kw in keywords:
            if kw in text:
                found[cat].append(kw)
    return found


def categorize_venue(venue) -> str:
    v = str(venue).lower()
    for cat, keywords in VENUE_MAP.items():
        for kw in keywords:
            if kw in v:
                return cat
    return "Other"


def focus_label(qid: str) -> str:
    if qid in ("Q1", "Q3"):
        return "Proactive (Design)"
    return "Diagnostic (Audit)"


def build_question_topics(rel: pd.DataFrame) -> dict:
    from collections import Counter

    q_topic_data = {}
    for qid in Q_ORDER:
        q_rows = rel[rel["question_id"] == qid]
        q_stats = {cat: Counter() for cat in TAXONOMY}
        for _, row in q_rows.iterrows():
            text = f"{row['title']} {row['abstract']} {row.get('directional_claim', '')}"
            ext = extract_keywords(text)
            for cat, kws in ext.items():
                q_stats[cat].update(kws)
        q_topic_data[qid] = {
            cat: [{"name": k, "value": v} for k, v in count.most_common(8)]
            for cat, count in q_stats.items()
        }
    return q_topic_data


def cluster_color(cluster_name: str, index: int = 0) -> str:
    for key, color in EDGE_COLORS.items():
        if key in str(cluster_name):
            return color
    return CLUSTER_PALETTE[index % len(CLUSTER_PALETTE)]


# ═══════════════════════════════════════════════════════════════════════
# Figure 1 — Papers per question (horizontal bar)
# ═══════════════════════════════════════════════════════════════════════
def fig1_papers_per_question(rel: pd.DataFrame):
    counts = rel.groupby("question_id").size().reindex(Q_ORDER).fillna(0).astype(int)

    fig, ax = plt.subplots(figsize=(8, 4.5), facecolor=BG_TRANSPARENT)
    bars = ax.barh(
        [Q_META[q]["short"] for q in Q_ORDER],
        [counts[q] for q in Q_ORDER],
        color=[Q_COLORS[q] for q in Q_ORDER],
        edgecolor="none",
        height=0.6,
        zorder=3,
    )

    # Value labels
    for bar, q in zip(bars, Q_ORDER):
        w = bar.get_width()
        ax.text(w + 3, bar.get_y() + bar.get_height() / 2,
                f"{int(w)}", va="center", ha="left",
                fontsize=11, fontweight="bold", color=TEXT_MAIN)

    ax.set_xlabel("Number of paper assignments")
    ax.invert_yaxis()
    ax.set_xlim(0, counts.max() * 1.15)
    ax.grid(axis="x", alpha=0.3)
    ax.grid(axis="y", visible=False)

    fig.tight_layout()
    save(fig, "fig1_papers_per_question")


# ═══════════════════════════════════════════════════════════════════════
# Figure 2 — Yearly trend (stacked area by question)
# ═══════════════════════════════════════════════════════════════════════
def fig2_yearly_trend(rel: pd.DataFrame):
    yearly = (rel.groupby(["year", "question_id"])
              .size()
              .unstack(fill_value=0)
              .reindex(columns=Q_ORDER, fill_value=0)
              .sort_index())

    fig, ax = plt.subplots(figsize=(9, 5), facecolor=BG_TRANSPARENT)
    years = yearly.index.values
    bottom = np.zeros(len(years))

    for q in Q_ORDER:
        vals = yearly[q].values
        ax.fill_between(years, bottom, bottom + vals,
                        label=Q_META[q]["short"],
                        color=Q_COLORS[q], alpha=0.85, linewidth=0)
        ax.plot(years, bottom + vals, color=Q_COLORS[q],
                linewidth=1.2, alpha=0.9)
        bottom = bottom + vals

    ax.set_xlabel("Year")
    ax.set_ylabel("Paper assignments")
    _style_legend(ax.legend(loc="upper left", ncol=3, frameon=True))
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax.set_xlim(years.min(), years.max())
    ax.set_ylim(0)

    fig.tight_layout()
    save(fig, "fig2_yearly_trend")


# ═══════════════════════════════════════════════════════════════════════
# Figure 3 — Edge (axis) distribution with breakdown
# ═══════════════════════════════════════════════════════════════════════
def fig3_edge_distribution(rel: pd.DataFrame):
    edges = {
        "Fairness \u2194 Explainability": {"qs": ["Q1", "Q2"], "cluster": "F\u2194E"},
        "Fairness \u2194 LLMs":           {"qs": ["Q3", "Q4"], "cluster": "F\u2194L"},
        "Explainability \u2194 LLMs":     {"qs": ["Q5", "Q6"], "cluster": "E\u2194L"},
    }

    counts = rel.groupby("question_id").size()
    edge_names = list(edges.keys())
    edge_totals = [sum(counts.get(q, 0) for q in e["qs"]) for e in edges.values()]
    edge_colors = [EDGE_COLORS[e["cluster"]] for e in edges.values()]

    fig, axes = plt.subplots(
        1, 2, figsize=(12, 5), gridspec_kw={"width_ratios": [1.5, 1]}, facecolor=BG_TRANSPARENT
    )

    # Left: horizontal grouped bar (each edge split into its 2 Qs)
    ax = axes[0]
    y_positions = np.arange(len(edge_names))
    bar_h = 0.35

    for i, (name, info) in enumerate(edges.items()):
        q_a, q_b = info["qs"]
        c_a = counts.get(q_a, 0)
        c_b = counts.get(q_b, 0)

        ax.barh(i - bar_h / 2, c_a, bar_h, color=Q_COLORS[q_a], edgecolor="none", zorder=3)
        ax.barh(i + bar_h / 2, c_b, bar_h, color=Q_COLORS[q_b], edgecolor="none", zorder=3)

        ax.text(c_a + 3, i - bar_h/2, f"{Q_META[q_a]['short']}: {c_a}",
                va="center", fontsize=9, color=TEXT_MAIN, fontweight="bold")
        ax.text(c_b + 3, i + bar_h/2, f"{Q_META[q_b]['short']}: {c_b}",
                va="center", fontsize=9, color=TEXT_MUTED)

    ax.set_yticks(y_positions)
    ax.set_yticklabels(edge_names, fontsize=10)
    ax.invert_yaxis()
    ax.set_xlabel("Paper assignments")
    ax.set_xlim(0, max(counts.values) * 1.3)
    ax.grid(axis="x", alpha=0.3)
    ax.grid(axis="y", visible=False)

    # Right: donut chart of total edge distribution
    ax2 = axes[1]
    wedges, texts, autotexts = ax2.pie(
        edge_totals, labels=None,
        colors=edge_colors, autopct="%1.0f%%",
        startangle=90, pctdistance=0.78,
        wedgeprops=dict(width=0.45, edgecolor=TEXT_MAIN, linewidth=1),
    )
    for t in autotexts:
        t.set_fontsize(11)
        t.set_fontweight("bold")
        t.set_color(TEXT_MAIN)

    # Center text
    ax2.text(0, 0, f"{sum(edge_totals)}\nassignments",
             ha="center", va="center", fontsize=13, fontweight="bold",
             color=TEXT_MAIN)

    ax2.legend(
        [f"{n}  ({t})" for n, t in zip(edge_names, edge_totals)],
        loc="lower center", bbox_to_anchor=(0.5, -0.15),
        fontsize=9, frameon=False, ncol=1
    )

    fig.tight_layout()
    save(fig, "fig3_edge_distribution")


# ═══════════════════════════════════════════════════════════════════════
# Figure 4 — Diagnostic vs. Proactive split
# ═══════════════════════════════════════════════════════════════════════
def fig4_diagnostic_vs_proactive(rel: pd.DataFrame):
    """
    Diagnostic (audit/post-hoc): Q2 (E->F), Q4 (L->F), Q6 (L->E)
    Proactive (design/pre-emptive): Q1 (F->E), Q3 (F->L), Q5 (E->L)
    """
    diag_qs = ["Q2", "Q4", "Q6"]
    proac_qs = ["Q1", "Q3", "Q5"]

    yearly = rel.groupby(["year", "question_id"]).size().unstack(fill_value=0)
    yearly["Diagnostic (Audit)"]  = yearly[diag_qs].sum(axis=1)
    yearly["Proactive (Design)"]  = yearly[proac_qs].sum(axis=1)

    fig, ax = plt.subplots(figsize=(8, 5), facecolor=BG_TRANSPARENT)
    width = 0.35
    years = yearly.index.values
    x = np.arange(len(years))

    ax.bar(x - width / 2, yearly["Proactive (Design)"], width,
           label="Proactive (Design)", color=FOCUS_COLORS["Proactive (Design)"],
           edgecolor="none", zorder=3)
    ax.bar(x + width / 2, yearly["Diagnostic (Audit)"], width,
           label="Diagnostic (Audit)", color=FOCUS_COLORS["Diagnostic (Audit)"],
           edgecolor="none", zorder=3)

    # Value labels on bars
    for i, yr in enumerate(years):
        p = yearly.loc[yr, "Proactive (Design)"]
        d = yearly.loc[yr, "Diagnostic (Audit)"]
        if p > 0:
            ax.text(i - width/2, p + 1.5, str(int(p)),
                    ha="center", va="bottom", fontsize=8, color=TEXT_MAIN, fontweight="bold")
        if d > 0:
            ax.text(i + width/2, d + 1.5, str(int(d)),
                    ha="center", va="bottom", fontsize=8, color=TEXT_MAIN, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels([str(int(y)) for y in years])
    ax.set_xlabel("Year")
    ax.set_ylabel("Paper assignments")
    _style_legend(ax.legend(loc="upper left", frameon=True))
    ax.grid(axis="y", alpha=0.3)
    ax.grid(axis="x", visible=False)

    fig.tight_layout()
    save(fig, "fig4_diagnostic_vs_proactive")


# ═══════════════════════════════════════════════════════════════════════
# Figure 5 — Top venues (horizontal bar)
# ═══════════════════════════════════════════════════════════════════════
def fig5_top_venues(rel: pd.DataFrame, top_n: int = 10):
    # Deduplicate: count each unique paper per venue only once
    papers = rel.drop_duplicates(subset=["title"]).copy()
    venue_counts = (papers["venue"]
                    .dropna()
                    .loc[lambda s: s != "nan"]
                    .str.strip()
                    .value_counts()
                    .head(top_n)
                    .iloc[::-1])  # reverse for horizontal bar

    fig, ax = plt.subplots(figsize=(12, 6), facecolor=BG_TRANSPARENT)
    colors = plt.cm.viridis(np.linspace(0.3, 0.85, len(venue_counts)))

    bars = ax.barh(venue_counts.index, venue_counts.values,
                   color=colors, edgecolor="none", height=0.65, zorder=3)

    for bar in bars:
        w = bar.get_width()
        ax.text(w + 0.3, bar.get_y() + bar.get_height() / 2,
                str(int(w)), va="center", ha="left",
                fontsize=9, fontweight="bold", color=TEXT_MAIN)

    ax.set_xlabel("Number of unique papers")
    ax.set_xlim(0, venue_counts.max() * 1.2)
    ax.grid(axis="x", alpha=0.3)
    ax.grid(axis="y", visible=False)

    fig.tight_layout()
    save(fig, "fig5_top_venues")


# ═══════════════════════════════════════════════════════════════════════
# Figure 6 — Multi-label distribution (how many Qs per paper)
# ═══════════════════════════════════════════════════════════════════════
def fig6_multilabel(rel: pd.DataFrame):
    # Match dashboard: assignment rows per unique title
    q_per_paper = rel.groupby("title").size()
    dist = q_per_paper.value_counts().sort_index()

    fig, ax = plt.subplots(figsize=(7, 4.5), facecolor=BG_TRANSPARENT)
    x = dist.index.values
    bar_colors = [DIRECTION_COUNT_COLORS.get(int(k), TEXT_MUTED) for k in x]
    bars = ax.bar(x, dist.values, color=bar_colors, edgecolor="none", width=0.6, zorder=3)

    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h + 2,
                str(int(h)), ha="center", va="bottom",
                fontsize=11, fontweight="bold", color=TEXT_MAIN)

    ax.set_xlabel("Directions covered per paper")
    ax.set_ylabel("Number of papers")
    ax.set_xticks(x)
    ax.grid(axis="y", alpha=0.3)
    ax.grid(axis="x", visible=False)

    # Annotation
    multi = int((q_per_paper >= 2).sum())
    total = int(q_per_paper.shape[0])
    ax.annotate(
        f"{multi}/{total} papers ({100*multi/total:.0f}%) span 2+ questions",
        xy=(2, dist.get(2, 0)), xytext=(3.5, dist.max() * 0.8),
        fontsize=10, color=Q_COLORS["Q1"], fontweight="bold",
        arrowprops=dict(arrowstyle="->", color=Q_COLORS["Q1"], lw=1.5),
    )

    fig.tight_layout()
    save(fig, "fig6_multilabel")


# ═══════════════════════════════════════════════════════════════════════
# Figure 7 — Pillar mention co-occurrence (Venn-like grouped bar)
# ═══════════════════════════════════════════════════════════════════════
def fig7_pillar_mentions(rel: pd.DataFrame):
    papers = rel.drop_duplicates(subset=["title"]).copy()
    papers["mentions_fairness"] = papers["mentions_fairness"].astype(bool)
    papers["mentions_xai"]      = papers["mentions_xai"].astype(bool)
    papers["mentions_llm"]      = papers["mentions_llm"].astype(bool)

    # Counts
    f_only  = ((papers.mentions_fairness) & ~(papers.mentions_xai) & ~(papers.mentions_llm)).sum()
    e_only  = (~(papers.mentions_fairness) & (papers.mentions_xai) & ~(papers.mentions_llm)).sum()
    l_only  = (~(papers.mentions_fairness) & ~(papers.mentions_xai) & (papers.mentions_llm)).sum()
    fe      = ((papers.mentions_fairness) & (papers.mentions_xai) & ~(papers.mentions_llm)).sum()
    fl      = ((papers.mentions_fairness) & ~(papers.mentions_xai) & (papers.mentions_llm)).sum()
    el      = (~(papers.mentions_fairness) & (papers.mentions_xai) & (papers.mentions_llm)).sum()
    all_3   = ((papers.mentions_fairness) & (papers.mentions_xai) & (papers.mentions_llm)).sum()
    none_   = (~(papers.mentions_fairness) & ~(papers.mentions_xai) & ~(papers.mentions_llm)).sum()

    labels = [
        "Fairness\nonly", "XAI\nonly", "LLM\nonly",
        "F + E", "F + L", "E + L",
        "All three", "None",
    ]
    values = [f_only, e_only, l_only, fe, fl, el, all_3, none_]
    colors_bar = [
        PILLAR_COLORS["Fairness"],
        PILLAR_COLORS["Explainability"],
        PILLAR_COLORS["LLMs"],
        PAIR_COLORS["Fairness \u2194 Explainability"],
        PAIR_COLORS["Fairness \u2194 LLMs"],
        PAIR_COLORS["Explainability \u2194 LLMs"],
        "#f0ab3d",
        TEXT_MUTED,
    ]

    fig, ax = plt.subplots(figsize=(10, 5), facecolor=BG_TRANSPARENT)
    x = np.arange(len(labels))
    bars = ax.bar(x, values, color=colors_bar, edgecolor="none", width=0.6, zorder=3)

    for bar in bars:
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, h + 1,
                    str(int(h)), ha="center", va="bottom",
                    fontsize=10, fontweight="bold", color=TEXT_MAIN)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("Number of unique papers")
    ax.grid(axis="y", alpha=0.3)
    ax.grid(axis="x", visible=False)

    fig.tight_layout()
    save(fig, "fig7_pillar_mentions")


# ═══════════════════════════════════════════════════════════════════════
# Figure 8 — Synergy Radar Chart (Paper counts per Q1-Q6)
# ═══════════════════════════════════════════════════════════════════════
def fig8_synergy_radar(rel: pd.DataFrame):
    counts = rel.groupby("question_id").size().reindex(Q_ORDER).fillna(0).astype(int)

    categories = [Q_META[q]["short"].replace(": ", ":\n") for q in Q_ORDER]
    N = len(categories)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]

    values = [counts[q] for q in Q_ORDER]
    values += values[:1]

    fig, ax = plt.subplots(
        figsize=(7, 7), subplot_kw=dict(polar=True), facecolor=BG_TRANSPARENT
    )

    # Draw Q1 at the top, rotate clockwise
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    # Draw labels with padding to prevent clipping
    plt.xticks(angles[:-1], categories, color=TEXT_MAIN, size=10, fontweight="bold")
    ax.tick_params(axis="x", pad=18)

    # Configure grid lines and y-ticks
    ax.set_rlabel_position(30)
    max_val = max(values)
    ticks = np.linspace(0, max_val, 5, dtype=int)
    plt.yticks(ticks, [str(t) for t in ticks], color=TEXT_MAIN, size=9, fontweight="bold")
    plt.ylim(0, max_val * 1.05)

    # Plot data
    ax.plot(angles, values, color=SYNERGY_RADAR_COLOR, linewidth=2.5, linestyle="solid", zorder=4)
    ax.fill(angles, values, color=SYNERGY_RADAR_COLOR, alpha=0.35, zorder=3)

    _style_polar_axes(ax)

    fig.subplots_adjust(left=0.18, right=0.82, top=0.82, bottom=0.18)
    save(fig, "fig8_synergy_radar")


# ═══════════════════════════════════════════════════════════════════════
# Figure 9 — Thematic Distribution Radar Chart (theme mentions by Q1-Q6)
# ═══════════════════════════════════════════════════════════════════════
def fig9_thematic_radar(rel: pd.DataFrame):
    categories = [Q_META[q]["short"].replace(": ", ":\n") for q in Q_ORDER]
    N = len(categories)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]

    # Calculate % for each pillar per question
    fairness_pcts = []
    xai_pcts = []
    llm_pcts = []
    for q in Q_ORDER:
        q_papers = rel[rel["question_id"] == q]
        total = len(q_papers) if len(q_papers) > 0 else 1
        fairness_pcts.append((q_papers["mentions_fairness"].sum() / total) * 100)
        xai_pcts.append((q_papers["mentions_xai"].sum() / total) * 100)
        llm_pcts.append((q_papers["mentions_llm"].sum() / total) * 100)

    # Close loops
    fairness_pcts += fairness_pcts[:1]
    xai_pcts += xai_pcts[:1]
    llm_pcts += llm_pcts[:1]

    fig, ax = plt.subplots(
        figsize=(7, 7), subplot_kw=dict(polar=True), facecolor=BG_TRANSPARENT
    )

    # Draw Q1 at the top, rotate clockwise
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    # Labels with padding
    plt.xticks(angles[:-1], categories, color=TEXT_MAIN, size=10, fontweight="bold")
    ax.tick_params(axis="x", pad=18)

    # Grid ticks (0% to 100%)
    ticks = [20, 40, 60, 80, 100]
    plt.yticks(ticks, [f"{t}%" for t in ticks], color=TEXT_MAIN, size=9, fontweight="bold")
    plt.ylim(0, 100)

    # Plot each pillar
    ax.plot(angles, fairness_pcts, color=PILLAR_COLORS["Fairness"], linewidth=2, label="Fairness", zorder=4)
    ax.fill(angles, fairness_pcts, color=PILLAR_COLORS["Fairness"], alpha=0.2, zorder=3)

    ax.plot(angles, xai_pcts, color=PILLAR_COLORS["Explainability"], linewidth=2, label="XAI", zorder=4)
    ax.fill(angles, xai_pcts, color=PILLAR_COLORS["Explainability"], alpha=0.2, zorder=3)

    ax.plot(angles, llm_pcts, color=PILLAR_COLORS["LLMs"], linewidth=2, label="LLMs", zorder=4)
    ax.fill(angles, llm_pcts, color=PILLAR_COLORS["LLMs"], alpha=0.2, zorder=3)

    _style_polar_axes(ax)

    _style_legend(plt.legend(loc="upper right", bbox_to_anchor=(1.22, 1.1), frameon=True))

    fig.subplots_adjust(left=0.18, right=0.82, top=0.82, bottom=0.18)
    save(fig, "fig9_thematic_radar")


# ═══════════════════════════════════════════════════════════════════════
# Figures 10–23 — Dashboard parity (insights tab + triangle)
# ═══════════════════════════════════════════════════════════════════════
def fig10_publication_cadence(rel: pd.DataFrame):
    papers = rel.drop_duplicates(subset=["title"]).copy()
    yearly = papers.dropna(subset=["year"]).groupby("year").size().sort_index()
    partial_cutoff = infer_partial_year_cutoff(papers)

    fig, ax = plt.subplots(figsize=(10, 5.5), facecolor=BG_TRANSPARENT)

    use_partial_cutoff = (
        partial_cutoff is not None
        and not yearly.empty
        and int(yearly.index.max()) == partial_cutoff.year
        and len(yearly) >= 2
    )

    if use_partial_cutoff:
        x_values = [pd.Timestamp(year=int(y), month=12, day=31) for y in yearly.index[:-1]]
        x_values.append(partial_cutoff)
        xticks = x_values
        xticklabels = [str(int(y)) for y in yearly.index[:-1]] + [partial_cutoff.strftime("%m/%Y")]
    else:
        x_values = yearly.index.tolist()

    # Gradient-style fill with layered alphas for depth
    ax.fill_between(x_values, yearly.values, color=CADENCE_COLOR, alpha=0.15, zorder=1)
    ax.fill_between(x_values, yearly.values, color=CADENCE_COLOR, alpha=0.20,
                    step=None, zorder=1)

    # Main line with markers
    ax.plot(x_values, yearly.values, color=CADENCE_COLOR, linewidth=2.8,
            marker="o", markersize=7, markerfacecolor="white",
            markeredgecolor=CADENCE_COLOR, markeredgewidth=2.2, zorder=4)

    # Data labels above each point
    for x, y in zip(x_values, yearly.values):
        ax.text(x, y + yearly.max() * 0.04, str(int(y)),
                ha="center", va="bottom", fontsize=10, fontweight="bold",
                color=TEXT_MAIN, zorder=5)

    ax.set_xlabel("Year")
    ax.set_ylabel("Number of papers")

    if use_partial_cutoff:
        ax.set_xticks(xticks)
        ax.set_xticklabels(xticklabels)
        ax.xaxis.set_minor_locator(mdates.MonthLocator(interval=3))
        ax.set_xlim(x_values[0] - pd.Timedelta(days=45), partial_cutoff)
    else:
        ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))

    ax.set_ylim(0, yearly.max() * 1.18)
    ax.grid(axis="y", alpha=0.3)
    ax.grid(axis="x", visible=False)

    fig.tight_layout()
    save(fig, "fig10_publication_cadence")


def fig11_directional_balance(rel: pd.DataFrame):
    counts = rel.groupby("question_id").size().reindex(Q_ORDER).fillna(0).astype(int)

    fig, ax = plt.subplots(figsize=(6, 6), facecolor=BG_TRANSPARENT)
    ax.pie(
        counts.values,
        labels=None,
        colors=[Q_COLORS[q] for q in Q_ORDER],
        autopct="%1.0f%%",
        startangle=90,
        pctdistance=0.78,
        wedgeprops=dict(width=0.45, edgecolor=TEXT_MAIN, linewidth=1),
    )
    for t in ax.texts:
        if "%" in t.get_text():
            t.set_fontweight("bold")
            t.set_color(TEXT_MAIN)
    _style_legend(
        ax.legend(
            [f"{Q_META[q]['short']} ({counts[q]})" for q in Q_ORDER],
            loc="center left",
            bbox_to_anchor=(1.02, 0.5),
            frameon=True,
        )
    )
    fig.tight_layout()
    save(fig, "fig11_directional_balance")


def fig12_maturity_matrix(rel: pd.DataFrame):
    points = []
    for q in Q_ORDER:
        q_rows = rel[rel["question_id"] == q]
        total = len(q_rows) or 1
        with_url = q_rows["url"].notna() & (q_rows["url"].astype(str) != "nan")
        multi = (
            q_rows["mentions_fairness"].astype(bool).astype(int)
            + q_rows["mentions_xai"].astype(bool).astype(int)
            + q_rows["mentions_llm"].astype(bool).astype(int)
        ) >= 2
        points.append({
            "q": q,
            "accessibility": with_url.sum() / total * 100,
            "depth": multi.sum() / total * 100,
            "count": len(q_rows),
        })

    fig, ax = plt.subplots(figsize=(8, 6), facecolor=BG_TRANSPARENT)
    for p in points:
        ax.scatter(
            p["accessibility"], p["depth"],
            s=80 + p["count"] * 4,
            color=Q_COLORS[p["q"]],
            edgecolors=TEXT_MAIN,
            linewidths=0.6,
            zorder=3,
            label=p["q"],
        )
        ax.annotate(p["q"], (p["accessibility"], p["depth"]),
                    fontsize=9, fontweight="bold", color=TEXT_MAIN,
                    xytext=(4, 4), textcoords="offset points")

    ax.set_xlabel("Accessibility (% with links)")
    ax.set_ylabel("Thematic depth (% multi-theme)")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.grid(alpha=0.35)
    fig.tight_layout()
    save(fig, "fig12_maturity_matrix")


def fig13_discipline_distribution(rel: pd.DataFrame):
    papers = unique_papers(rel)
    papers = papers.copy()
    papers["venue_cat"] = papers["venue"].apply(categorize_venue)
    dist = papers["venue_cat"].value_counts()

    fig, ax = plt.subplots(figsize=(6, 6), facecolor=BG_TRANSPARENT)
    colors = [DISCIPLINE_PALETTE[i % len(DISCIPLINE_PALETTE)] for i in range(len(dist))]
    ax.pie(
        dist.values,
        labels=None,
        colors=colors,
        autopct="%1.0f%%",
        startangle=90,
        pctdistance=0.78,
        wedgeprops=dict(width=0.45, edgecolor=TEXT_MAIN, linewidth=1),
    )
    for t in ax.texts:
        if "%" in t.get_text():
            t.set_fontweight("bold")
            t.set_color(TEXT_MAIN)
    _style_legend(
        ax.legend(
            [f"{n} ({v})" for n, v in zip(dist.index, dist.values)],
            loc="center left",
            bbox_to_anchor=(1.02, 0.5),
            frameon=True,
        )
    )
    fig.tight_layout()
    save(fig, "fig13_discipline_distribution")


def fig14_methodology_distribution(rel: pd.DataFrame, question_topics: dict):
    x = np.arange(len(Q_ORDER))
    width = 0.65
    bottom = np.zeros(len(Q_ORDER))

    fig, ax = plt.subplots(figsize=(10, 5), facecolor=BG_TRANSPARENT)
    for mtype in METHODOLOGY_TYPES:
        vals = []
        for q in Q_ORDER:
            topics = question_topics[q].get("Paper Type", [])
            found = next((t["value"] for t in topics if t["name"] == mtype), 0)
            vals.append(found)
        ax.bar(x, vals, width, bottom=bottom, label=mtype.capitalize(),
               color=METHODOLOGY_COLORS[mtype], edgecolor="none", zorder=3)
        bottom += np.array(vals)

    ax.set_xticks(x)
    ax.set_xticklabels(Q_ORDER)
    ax.set_ylabel("Keyword hits (assignments)")
    _style_legend(
        ax.legend(
            loc="upper center",
            bbox_to_anchor=(0.5, -0.12),
            ncol=4,
            frameon=True,
        )
    )
    ax.grid(axis="y", alpha=0.3)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.22)
    save(fig, "fig14_methodology_distribution")


def fig15_topical_coverage(rel: pd.DataFrame):
    papers = unique_papers(rel)
    stats = {
        "Fairness mentions": int(papers["mentions_fairness"].astype(bool).sum()),
        "Explainability mentions": int(papers["mentions_xai"].astype(bool).sum()),
        "LLM mentions": int(papers["mentions_llm"].astype(bool).sum()),
    }
    labels = list(stats.keys())
    values = list(stats.values())
    colors = [
        PILLAR_COLORS["Fairness"],
        PILLAR_COLORS["Explainability"],
        PILLAR_COLORS["LLMs"],
    ]

    fig, ax = plt.subplots(figsize=(7, 4.5), facecolor=BG_TRANSPARENT)
    y = np.arange(len(labels))
    bars = ax.barh(y, values, color=colors, edgecolor="none", height=0.55, zorder=3)
    for bar, val in zip(bars, values):
        ax.text(val + 2, bar.get_y() + bar.get_height() / 2, str(val),
                va="center", fontsize=10, fontweight="bold", color=TEXT_MAIN)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("Unique papers")
    ax.grid(axis="x", alpha=0.3)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    save(fig, "fig15_topical_coverage")


def fig16_comention_intensity(rel: pd.DataFrame):
    papers = unique_papers(rel)
    f = papers["mentions_fairness"].astype(bool)
    e = papers["mentions_xai"].astype(bool)
    l = papers["mentions_llm"].astype(bool)
    pairs = {
        "Fairness \u2194 Explainability": int((f & e).sum()),
        "Fairness \u2194 LLMs": int((f & l).sum()),
        "Explainability \u2194 LLMs": int((e & l).sum()),
    }

    labels = list(pairs.keys())
    values = [pairs[k] for k in labels]
    colors = [PAIR_COLORS[k] for k in labels]

    fig, ax = plt.subplots(figsize=(7, 4.5), facecolor=BG_TRANSPARENT)
    y = np.arange(len(labels))
    bars = ax.barh(y, values, color=colors, edgecolor="none", height=0.55, zorder=3)
    for bar, val in zip(bars, values):
        ax.text(val + 1, bar.get_y() + bar.get_height() / 2, str(val),
                va="center", fontsize=10, fontweight="bold", color=TEXT_MAIN)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("Unique papers")
    ax.grid(axis="x", alpha=0.3)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    save(fig, "fig16_comention_intensity")


def fig17_maturity_trends(rel: pd.DataFrame):
    rows = []
    for year, grp in rel.dropna(subset=["year"]).groupby("year"):
        total = len(grp) or 1
        with_url = grp["url"].notna() & (grp["url"].astype(str) != "nan")
        multi = (
            grp["mentions_fairness"].astype(bool).astype(int)
            + grp["mentions_xai"].astype(bool).astype(int)
            + grp["mentions_llm"].astype(bool).astype(int)
        ) >= 2
        rows.append({
            "year": int(year),
            "accessibility": with_url.sum() / total * 100,
            "depth": multi.sum() / total * 100,
        })
    trends = pd.DataFrame(rows).sort_values("year")

    fig, ax = plt.subplots(figsize=(9, 5), facecolor=BG_TRANSPARENT)
    ax.plot(trends["year"], trends["accessibility"],
            color=MATURITY_LINE_COLORS["accessibility"], linewidth=2.5,
            marker="o", markersize=6, label="Accessibility (% URLs)")
    ax.plot(trends["year"], trends["depth"],
            color=MATURITY_LINE_COLORS["depth"], linewidth=2.5,
            marker="o", markersize=6, label="Thematic depth (% multi-theme)")
    ax.set_xlabel("Year")
    ax.set_ylabel("Percentage")
    ax.set_ylim(0, 100)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    _style_legend(ax.legend(loc="upper left", frameon=True))
    ax.grid(alpha=0.35)
    fig.tight_layout()
    save(fig, "fig17_maturity_trends")


def fig18_model_lineage(rel: pd.DataFrame):
    papers = unique_papers(rel)
    rows = []
    for year in sorted(papers["year"].dropna().unique()):
        yp = papers[papers["year"] == year]
        row = {"year": int(year)}
        for family, key in [("gpt", "gpt"), ("llama", "llama"), ("bert", "bert")]:
            row[family] = int(yp.apply(
                lambda r: key in str(r["title"]).lower() or key in str(r["abstract"]).lower(),
                axis=1,
            ).sum())
        rows.append(row)
    evo = pd.DataFrame(rows)

    fig, ax = plt.subplots(figsize=(9, 5), facecolor=BG_TRANSPARENT)
    years = evo["year"].values
    bottom = np.zeros(len(years))
    for family in ("gpt", "llama", "bert"):
        vals = evo[family].values
        ax.fill_between(years, bottom, bottom + vals,
                        label=family.upper() if family == "gpt" else family.capitalize(),
                        color=MODEL_FAMILY_COLORS[family], alpha=0.75, linewidth=0)
        ax.plot(years, bottom + vals, color=MODEL_FAMILY_COLORS[family], linewidth=1.5)
        bottom = bottom + vals

    ax.set_xlabel("Year")
    ax.set_ylabel("Unique papers mentioning family")
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    _style_legend(ax.legend(loc="upper left", frameon=True))
    fig.tight_layout()
    save(fig, "fig18_model_lineage")


def fig19_focus_evolution(rel: pd.DataFrame):
    df = rel.copy()
    df["focus"] = df["question_id"].map(focus_label)
    yearly = df.groupby(["year", "focus"]).size().unstack(fill_value=0).sort_index()

    fig, ax = plt.subplots(figsize=(9, 5), facecolor=BG_TRANSPARENT)
    years = yearly.index.values
    x = np.arange(len(years))
    width = 0.55

    for i, col in enumerate(["Diagnostic (Audit)", "Proactive (Design)"]):
        if col not in yearly.columns:
            continue
        offset = -width / 2 if col == "Diagnostic (Audit)" else width / 2
        ax.bar(x + offset, yearly[col], width, label=col,
               color=FOCUS_COLORS[col], edgecolor="none", zorder=3)

    ax.set_xticks(x)
    ax.set_xticklabels([str(int(y)) for y in years])
    ax.set_xlabel("Year")
    ax.set_ylabel("Paper assignments")
    _style_legend(ax.legend(loc="upper left", frameon=True))
    ax.grid(axis="y", alpha=0.3)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    save(fig, "fig19_focus_evolution")


def fig20_taxonomy_paper_type(question_topics: dict):
    fig, axes = plt.subplots(2, 3, figsize=(14, 8), facecolor=BG_TRANSPARENT)
    axes = axes.flatten()
    category = "Paper Type"

    for ax, q in zip(axes, Q_ORDER):
        topics = question_topics[q].get(category, [])
        if not topics:
            ax.set_visible(False)
            continue
        names = [t["name"] for t in topics]
        vals = [t["value"] for t in topics]
        colors = [TAXONOMY_BAR_PALETTE[i % len(TAXONOMY_BAR_PALETTE)] for i in range(len(names))]
        y = np.arange(len(names))
        ax.barh(y, vals, color=colors, edgecolor="none", height=0.6)
        ax.set_yticks(y)
        ax.set_yticklabels(names, fontsize=8)
        ax.invert_yaxis()
        ax.set_title(q, fontsize=11, fontweight="bold", color=Q_COLORS[q])
        ax.grid(axis="x", alpha=0.25)
        ax.grid(axis="y", visible=False)

    fig.tight_layout()
    save(fig, "fig20_taxonomy_paper_type")


def fig21_research_clusters(rel: pd.DataFrame):
    counts = rel.groupby("cluster").size().sort_values(ascending=False)
    colors = [cluster_color(c, i) for i, c in enumerate(counts.index)]

    fig, ax = plt.subplots(figsize=(6, 6), facecolor=BG_TRANSPARENT)
    ax.pie(
        counts.values,
        labels=None,
        colors=colors,
        autopct="%1.0f%%",
        startangle=90,
        pctdistance=0.78,
        wedgeprops=dict(width=0.45, edgecolor=TEXT_MAIN, linewidth=1),
    )
    for t in ax.texts:
        if "%" in t.get_text():
            t.set_fontweight("bold")
            t.set_color(TEXT_MAIN)
    _style_legend(
        ax.legend(
            [f"{n} ({v})" for n, v in counts.items()],
            loc="center left",
            bbox_to_anchor=(1.02, 0.5),
            frameon=True,
        )
    )
    fig.tight_layout()
    save(fig, "fig21_research_clusters")


def fig22_keyword_frequency(rel: pd.DataFrame):
    from collections import Counter

    papers = unique_papers(rel)
    word_counts: Counter = Counter()
    for title in papers["title"].dropna():
        for word in str(title).lower().split():
            w = "".join(ch for ch in word if ch.isalnum())
            if len(w) > 3 and w not in TITLE_STOP_WORDS and not w.isdigit():
                word_counts[w] += 1

    top = word_counts.most_common(20)
    if not top:
        return

    labels = [w.capitalize() for w, _ in reversed(top)]
    values = [v for _, v in reversed(top)]
    colors = [KEYWORD_PALETTE[i % len(KEYWORD_PALETTE)] for i in range(len(labels))]

    fig, ax = plt.subplots(figsize=(9, 6), facecolor=BG_TRANSPARENT)
    y = np.arange(len(labels))
    ax.barh(y, values, color=colors, edgecolor="none", height=0.65, zorder=3)
    for bar, val in zip(ax.patches, values):
        ax.text(val + 0.3, bar.get_y() + bar.get_height() / 2, str(val),
                va="center", fontsize=9, fontweight="bold", color=TEXT_MAIN)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Occurrences in titles")
    ax.grid(axis="x", alpha=0.3)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    save(fig, "fig22_keyword_frequency")


def fig23_relationship_triangle(rel: pd.DataFrame):
    counts = rel.groupby("cluster").size()
    fe = int(counts.get("F\u2194E", 0))
    fl = int(counts.get("F\u2194L", 0))
    el = int(counts.get("E\u2194L", 0))

    fig, ax = plt.subplots(figsize=(7, 6.5), facecolor=BG_TRANSPARENT)
    ax.set_aspect("equal")
    ax.axis("off")

    # Equilateral triangle vertices (Fairness top)
    verts = np.array([[0.5, 0.92], [0.08, 0.12], [0.92, 0.12]])
    labels = ["Fairness", "Explainability", "LLMs"]
    edge_mid = [
        ((verts[0] + verts[1]) / 2, "F\u2194E", fe, EDGE_COLORS["F\u2194E"]),
        ((verts[0] + verts[2]) / 2, "F\u2194L", fl, EDGE_COLORS["F\u2194L"]),
        ((verts[1] + verts[2]) / 2, "E\u2194L", el, EDGE_COLORS["E\u2194L"]),
    ]

    triangle = plt.Polygon(verts, closed=True, fill=False,
                           edgecolor=POLAR_SPINE_COLOR, linewidth=2, zorder=1)
    ax.add_patch(triangle)

    for v, lab in zip(verts, labels):
        ax.scatter(v[0], v[1], s=120, color=PILLAR_COLORS.get(lab, TEXT_MAIN), zorder=3,
                   edgecolors=TEXT_MAIN, linewidths=1)
        offset = [0, 0.06] if lab == "Fairness" else [-0.12, -0.05] if lab == "Explainability" else [0.05, -0.05]
        ax.text(v[0] + offset[0], v[1] + offset[1], lab,
                ha="center", va="center", fontsize=11, fontweight="bold", color=TEXT_MAIN)

    for mid, edge_name, count, color in edge_mid:
        ax.text(mid[0], mid[1], f"{edge_name}\n{count}",
                ha="center", va="center", fontsize=10, fontweight="bold", color=color)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.tight_layout()
    save(fig, "fig23_relationship_triangle")


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════
def main():
    setup_style()
    print(f"Loading data from {INPUT_CSV} ...")
    df_all, rel = load_data()

    total_papers = rel["title"].nunique()
    total_assign = len(rel)
    print(f"  {total_papers} unique papers, {total_assign} assignments\n")

    print("Building taxonomy (for methodology / taxonomy figures) ...")
    question_topics = build_question_topics(rel)

    print("Generating figures:")
    fig1_papers_per_question(rel)
    fig2_yearly_trend(rel)
    fig3_edge_distribution(rel)
    fig4_diagnostic_vs_proactive(rel)
    fig5_top_venues(rel)
    fig6_multilabel(rel)
    fig7_pillar_mentions(rel)
    fig8_synergy_radar(rel)
    fig9_thematic_radar(rel)
    fig10_publication_cadence(rel)
    fig11_directional_balance(rel)
    fig12_maturity_matrix(rel)
    fig13_discipline_distribution(rel)
    fig14_methodology_distribution(rel, question_topics)
    fig15_topical_coverage(rel)
    fig16_comention_intensity(rel)
    fig17_maturity_trends(rel)
    fig18_model_lineage(rel)
    fig19_focus_evolution(rel)
    fig20_taxonomy_paper_type(question_topics)
    fig21_research_clusters(rel)
    fig22_keyword_frequency(rel)
    fig23_relationship_triangle(rel)

    print(f"\nAll figures saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
