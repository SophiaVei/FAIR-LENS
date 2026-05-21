#!/usr/bin/env python3
"""
plot_figures.py
Publication-quality figures for the FAIR-LENS systematic review.
Reads outputs/tri_results_master.csv and writes high-res PNGs + PDFs
to outputs/figures/.

Usage:
    python plot_figures.py
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from pathlib import Path
import numpy as np
from matplotlib.patches import FancyBboxPatch
import matplotlib.patheffects as pe

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

# Pillar colors (used for the three vertices of the triangle)
PILLAR_COLORS = {
    "Fairness":       "#e76f51",  # Deep terracotta orange
    "Explainability": "#2a7f3f",  # Deep green
    "LLMs":           "#1d4e89",  # Deep blue
}

# Edge/axis colors
EDGE_COLORS = {
    "F\u2194E": "#f4a261",   # orange
    "F\u2194L": "#1d4e89",   # dark blue
    "E\u2194L": "#2a7f3f",   # forest green
}

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
        "Fairness \u2194 Explainability": {"qs": ["Q1", "Q2"], "color": "#f4a261"},
        "Fairness \u2194 LLMs":           {"qs": ["Q3", "Q4"], "color": "#3a86a8"},
        "Explainability \u2194 LLMs":     {"qs": ["Q5", "Q6"], "color": "#4a9a5e"},
    }

    counts = rel.groupby("question_id").size()
    edge_names = list(edges.keys())
    edge_totals = [sum(counts.get(q, 0) for q in e["qs"]) for e in edges.values()]
    edge_colors = [e["color"] for e in edges.values()]

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
        col = info["color"]

        b1 = ax.barh(i - bar_h/2, c_a, bar_h, color=col, alpha=0.9, zorder=3)
        b2 = ax.barh(i + bar_h/2, c_b, bar_h, color=col, alpha=0.55, zorder=3)

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

    ax.bar(x - width/2, yearly["Proactive (Design)"], width,
           label="Proactive (Design)", color="#f4a261", edgecolor="none", zorder=3)
    ax.bar(x + width/2, yearly["Diagnostic (Audit)"], width,
           label="Diagnostic (Audit)", color="#8ecae6", edgecolor="none", zorder=3)

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
def fig5_top_venues(rel: pd.DataFrame, top_n: int = 15):
    # Deduplicate: count each unique paper per venue only once
    papers = rel.drop_duplicates(subset=["title"]).copy()
    venue_counts = (papers["venue"]
                    .dropna()
                    .loc[lambda s: s != "nan"]
                    .str.strip()
                    .value_counts()
                    .head(top_n)
                    .iloc[::-1])  # reverse for horizontal bar

    fig, ax = plt.subplots(figsize=(9, 6), facecolor=BG_TRANSPARENT)
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
    q_per_paper = rel.groupby("title")["question_id"].nunique()
    dist = q_per_paper.value_counts().sort_index()

    fig, ax = plt.subplots(figsize=(7, 4.5), facecolor=BG_TRANSPARENT)
    x = dist.index.values
    bars = ax.bar(x, dist.values,
                  color=["#577590", "#43aa8b", "#90be6d", "#f9c74f", "#f9844a", "#f4a261"][:len(x)],
                  edgecolor="none", width=0.6, zorder=3)

    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h + 2,
                str(int(h)), ha="center", va="bottom",
                fontsize=11, fontweight="bold", color=TEXT_MAIN)

    ax.set_xlabel("Number of questions addressed per paper")
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
        fontsize=10, color="#d97706", fontweight="bold",
        arrowprops=dict(arrowstyle="->", color="#d97706", lw=1.5),
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
        "All three", "None"
    ]
    values = [f_only, e_only, l_only, fe, fl, el, all_3, none_]
    colors_bar = [
        "#f4a261", "#a3b18a", "#8ecae6",
        "#d4956a", "#b87a44", "#6aaa99",
        "#f0ab3d", "#4b5563"
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
    ax.plot(angles, values, color="#6366f1", linewidth=2.5, linestyle="solid", zorder=4)
    ax.fill(angles, values, color="#6366f1", alpha=0.35, zorder=3)

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
# Main
# ═══════════════════════════════════════════════════════════════════════
def main():
    setup_style()
    print(f"Loading data from {INPUT_CSV} ...")
    df_all, rel = load_data()

    total_papers = rel["title"].nunique()
    total_assign = len(rel)
    print(f"  {total_papers} unique papers, {total_assign} assignments\n")

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

    print(f"\nAll figures saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
