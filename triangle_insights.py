#!/usr/bin/env python3
"""
Triangle Insights Visualization (Enhanced Aesthetic Version + Counts)

Generates publication trends and descriptive analytics
from the triangle LLM screening outputs.

It also prints detailed counts so we can track how many papers
survive each stage of the pipeline (LENS -> prefilter -> questions).

Inputs:
    - outputs/tri_results_master.csv   (from questions.py)
    - outputs/prefilter_report.md      (from exclude_final.py, optional)

Outputs (plots):
    - outputs/plots/triangle_trends.html / .png
    - outputs/plots/cluster_distribution.html / .png
    - outputs/plots/subcluster_heatmap.png
    - outputs/plots/venues_top.html / .png
    - outputs/plots/triangle_sunburst.html

Console output (counts):
    - LENS total / prefilter kept & dropped  (parsed from prefilter_report.md)
    - unique papers in tri_results_master.csv (before & after relevant==True)
    - per-question counts (rows + unique papers)
    - final number of papers used for plots
"""

import argparse
import re
from pathlib import Path

import pandas as pd
import plotly.express as px

import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap


# -----------------------
# GLOBAL AESTHETICS
# -----------------------

PLOT_BG = "#FFFFFF"
PAPER_BG = "#FFFFFF"
GRID_COLOR = "#E3E0DB"
TEXT_COLOR = "#1F2933"

EARTHY_6 = [
    "#386641",  # deep olive
    "#A98467",  # warm brown
    "#6C757D",  # slate grey
    "#B56576",  # muted rose
    "#A3B18A",  # sage
    "#D4A373",  # sand
]

PASTEL_EARTH = [
    "#C9D6B8",
    "#F2C6A0",
    "#E8D9B5",
    "#C7B8EA",
    "#F3B5B3",
    "#B0C4B1",
    "#F6DFAE",
    "#D8B4A0",
    "#D5E2C6",
    "#E3C1D3",
]

sns.set_theme(
    style="white",
    context="talk",
    rc={
        "axes.edgecolor": GRID_COLOR,
        "axes.labelcolor": TEXT_COLOR,
        "xtick.color": TEXT_COLOR,
        "ytick.color": TEXT_COLOR,
        "text.color": TEXT_COLOR,
    },
)


# -----------------------
# DATA LOADING + COUNTS
# -----------------------

def load_master(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load tri_results_master.csv and return:
      - df_all:   ALL rows (relevant True/False)
      - df_rel:   only rows with relevant == True (used for plots)
    """
    df_all = pd.read_csv(path)
    df_all["year"] = pd.to_numeric(df_all["year"], errors="coerce")

    if "relevant" not in df_all.columns:
        raise ValueError("tri_results_master.csv is missing 'relevant' column.")

    df_rel = df_all[df_all["relevant"] == True].copy()
    return df_all, df_rel


def _unique_paper_count(df: pd.DataFrame) -> int:
    """
    Count unique papers using (title, year, url) if available.
    Falls back gracefully if some columns are missing.
    """
    cols = [c for c in ["title", "year", "url"] if c in df.columns]
    if not cols:
        # worst case: count rows
        return len(df)
    return df[cols].drop_duplicates().shape[0]


def print_pipeline_counts(
    df_all: pd.DataFrame,
    df_rel: pd.DataFrame,
    prefilter_report_path: Path,
):
    """
    Print:
      - counts from prefilter_report.md (LENS + E0–E2)
      - counts from tri_results_master.csv (before & after relevant filter)
      - per-question counts
    """
    print("\n================ TRIANGLE PIPELINE COUNTS ================\n")

    # ---- 1) Prefilter / LENS stage (from prefilter_report.md) ----
    if prefilter_report_path.exists():
        text = prefilter_report_path.read_text(encoding="utf-8", errors="ignore")
        total_input = re.search(r"Total input:\s*(\d+)", text)
        kept = re.search(r"Kept:\s*(\d+)", text)
        dropped = re.search(r"Dropped:\s*(\d+)", text)

        print("[Stage 0–1] LENS search + E0–E2 prefilter (from prefilter_report.md)")
        if total_input:
            print(f"  • Total input from LENS:           {int(total_input.group(1))}")
        else:
            print("  • Total input:                     (not found in report)")
        if kept:
            print(f"  • Kept after E0–E2 filter:         {int(kept.group(1))}")
        if dropped:
            print(f"  • Dropped by E0–E2 filter:         {int(dropped.group(1))}")
        print()
    else:
        print("[Stage 0–1] prefilter_report.md not found; "
              "skipping LENS / E0–E2 summary.\n")

    # ---- 2) Questions stage → tri_results_master.csv ----
    n_rows_all = len(df_all)
    n_unique_all = _unique_paper_count(df_all)

    n_rows_rel = len(df_rel)
    n_unique_rel = _unique_paper_count(df_rel)

    print("[Stage 2] questions.py → tri_results_master.csv")
    print(f"  • Rows in master (all, rel+non-rel):         {n_rows_all}")
    print(f"  • Unique papers in master (all):            {n_unique_all}")
    print(f"  • Rows with relevant == True:               {n_rows_rel}")
    print(f"  • Unique papers with relevant == True:      {n_unique_rel}")

    # if we know prefilter 'kept', approximate how many questions.py removed
    if prefilter_report_path.exists():
        text = prefilter_report_path.read_text(encoding="utf-8", errors="ignore")
        kept = re.search(r"Kept:\s*(\d+)", text)
        if kept:
            kept_prefilter = int(kept.group(1))
            diff = kept_prefilter - n_unique_rel
            print(f"  • Approx. dropped by questions step:        {diff} "
                  f"(= {kept_prefilter} prefilter kept - {n_unique_rel} relevant)")
    print()

    # ---- 3) Per-question stats (only relevant==True are used for plots) ----
    df_q = df_rel.copy()
    df_q["qid"] = (
        df_q["question_id"]
        .astype(str)
        .str.extract(r"(Q[1-6])", expand=False)
    )
    df_q = df_q[df_q["qid"].notna()]

    # rows per question (each row is a paper–question assignment)
    row_counts = df_q.groupby("qid").size()

    # unique papers per question
    cols = [c for c in ["title", "year", "url"] if c in df_q.columns]
    if cols:
        uniq_counts = (
            df_q.groupby("qid")[cols]
            .apply(lambda x: x.drop_duplicates().shape[0])
        )
    else:
        uniq_counts = row_counts.copy()

    q_labels = {
        "Q1": "Q1 (F→E)",
        "Q2": "Q2 (E→F)",
        "Q3": "Q3 (F→LLMs)",
        "Q4": "Q4 (LLMs→F)",
        "Q5": "Q5 (E→LLMs)",
        "Q6": "Q6 (LLMs→E)",
    }

    print("[Stage 3] Per-question usage (only relevant==True)")
    print("  Question        Rows   Unique papers")
    print("  ------------------------------------")
    for qid in sorted(row_counts.index):
        rows = int(row_counts[qid])
        uniq = int(uniq_counts[qid])
        label = q_labels.get(qid, qid)
        print(f"  {label:<13} {rows:4d}   {uniq:4d}")
    print()

    # sanity: how many unique relevant papers have at least one question
    if cols:
        n_rel_with_q = (
            df_q[cols].drop_duplicates().shape[0]
        )
        print(f"  • Unique relevant papers with ≥1 question:  {n_rel_with_q}")
        print(f"  • Unique relevant papers overall:           {n_unique_rel}")
    print("\n================ END COUNTS ================\n")


# -----------------------
# PLOT HELPERS
# -----------------------

def style_plotly(fig, title, xlab, ylab):
    fig.update_layout(
        title=dict(text=title, x=0.5, y=0.95),
        plot_bgcolor=PLOT_BG,
        paper_bgcolor=PAPER_BG,
        font=dict(family="DejaVu Sans", size=16, color=TEXT_COLOR),
        xaxis=dict(title=xlab, showgrid=True, gridcolor=GRID_COLOR),
        yaxis=dict(title=ylab, showgrid=True, gridcolor=GRID_COLOR),
        margin=dict(l=80, r=40, t=100, b=100),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.20,
            x=0.5,
            xanchor="center",
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor=GRID_COLOR,
            borderwidth=1,
        ),
    )
    return fig


# -----------------------
# PLOTS
# -----------------------

def plot_yearly_trends(df: pd.DataFrame, outdir: Path):
    df2 = df.copy()
    df2["qid"] = df2["question_id"].astype(str).str.extract(r"(Q[1-6])")
    df2 = df2[df2["year"].notna() & df2["qid"].notna()]

    trend = (
        df2.groupby(["qid", "year"])
        .size()
        .reset_index(name="count")
        .sort_values(["qid", "year"])
    )

    q_labels = {
        "Q1": "Q1 (F→E)",
        "Q2": "Q2 (E→F)",
        "Q3": "Q3 (F→LLMs)",
        "Q4": "Q4 (LLMs→F)",
        "Q5": "Q5 (E→LLMs)",
        "Q6": "Q6 (LLMs→E)",
    }
    trend["Question"] = trend["qid"].map(q_labels)

    fig = px.line(
        trend,
        x="year",
        y="count",
        color="Question",
        markers=True,
        color_discrete_sequence=EARTHY_6,
    )

    fig.update_traces(
        line=dict(width=3),
        marker=dict(size=9, line=dict(width=1.2, color="white")),
    )

    fig = style_plotly(
        fig,
        "Yearly Publication Trends per Question",
        "Publication Year",
        "Number of Papers",
    )

    fig.write_html(outdir / "triangle_trends.html")
    fig.write_image(outdir / "triangle_trends.png", scale=2)
    print("[PLOT] Saved yearly trends")


def plot_cluster_distribution(df: pd.DataFrame, outdir: Path):
    counts = df.groupby("cluster").size().reset_index(name="count")

    fig = px.bar(
        counts,
        x="cluster",
        y="count",
        text="count",
        color="cluster",
        color_discrete_sequence=PASTEL_EARTH,
    )

    fig.update_traces(textposition="outside")

    fig = style_plotly(
        fig,
        "Relevant Papers per Cluster",
        "Cluster",
        "Number of Papers",
    )

    fig.write_html(outdir / "cluster_distribution.html")
    fig.write_image(outdir / "cluster_distribution.png", scale=2)
    print("[PLOT] Saved cluster distribution")


def plot_subcluster_heatmap(df: pd.DataFrame, outdir: Path):
    pivot = (
        df.groupby(["cluster", "subcluster"])
        .size()
        .reset_index(name="count")
        .pivot(index="cluster", columns="subcluster", values="count")
        .fillna(0)
    )

    cmap = LinearSegmentedColormap.from_list(
        "earth_heat",
        ["#FFFFFF", "#EDDCC2", "#C8C4A0", "#8FB996", "#386641"],
    )

    plt.figure(figsize=(12, 6), facecolor="white")
    ax = sns.heatmap(
        pivot,
        cmap=cmap,
        annot=True,
        fmt=".0f",
        linewidths=0.5,
        linecolor=GRID_COLOR,
        cbar=False,
        annot_kws={"color": TEXT_COLOR},
    )

    ax.set_title("Subcluster Density Heatmap", fontsize=18, pad=16)
    ax.set_xlabel("Subcluster")
    ax.set_ylabel("Cluster")

    plt.tight_layout()
    plt.savefig(outdir / "subcluster_heatmap.png", dpi=220, facecolor="white")
    plt.close()

    print("[PLOT] Saved subcluster heatmap")


def plot_venue_cloud(df: pd.DataFrame, outdir: Path):
    venue_counts = (
        df["venue"]
        .dropna()
        .value_counts()
        .head(15)
        .reset_index()
    )
    venue_counts.columns = ["venue", "venue_count"]

    fig = px.bar(
        venue_counts,
        x="venue_count",
        y="venue",
        orientation="h",
        color="venue_count",
        color_continuous_scale=["#F5EDE2", "#C9D6B8", "#8FB996", "#386641"],
    )

    fig.update_layout(coloraxis_showscale=False)

    fig = style_plotly(
        fig,
        "Top 15 Venues for Relevant Papers",
        "Number of Papers",
        "Venue",
    )

    fig.update_layout(
        yaxis=dict(categoryorder="total ascending")
    )

    fig.write_html(outdir / "venues_top.html")
    fig.write_image(outdir / "venues_top.png", scale=2)
    print("[PLOT] Saved venue distribution")


def plot_interrelation_chord(df: pd.DataFrame, outdir: Path):
    pairs = (
        df.groupby(["cluster", "subcluster"])
        .size()
        .reset_index(name="count")
    )

    fig = px.sunburst(
        pairs,
        path=["cluster", "subcluster"],
        values="count",
        color="cluster",
        color_discrete_sequence=PASTEL_EARTH,
    )

    fig.update_traces(insidetextorientation="radial")

    fig = style_plotly(
        fig,
        "Hierarchical Relationships Between Clusters and Directions",
        "",
        "",
    )

    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=30, r=30, t=100, b=30),
    )

    fig.write_html(outdir / "triangle_sunburst.html")
    print("[PLOT] Saved sunburst plot")


# -----------------------
# MAIN
# -----------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--input",
        type=str,
        default="outputs/tri_results_master.csv",
        help="Path to tri_results_master.csv (from questions.py).",
    )
    ap.add_argument(
        "--prefilter_report",
        type=str,
        default="outputs/prefilter_report.md",
        help="Path to prefilter_report.md (from exclude_final.py).",
    )
    ap.add_argument(
        "--outdir",
        type=str,
        default="outputs/plots",
        help="Directory for output plots.",
    )
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(exist_ok=True, parents=True)

    master_path = Path(args.input)
    prefilter_report_path = Path(args.prefilter_report)

    print(f"[INFO] Loading master: {master_path}")
    df_all, df_rel = load_master(master_path)

    # Print all the counts you asked for
    print_pipeline_counts(df_all, df_rel, prefilter_report_path)

    # Plots use only relevant==True rows
    print(f"[INFO] Using {len(df_rel)} rows (relevant==True) for plots.")
    plot_yearly_trends(df_rel, outdir)
    plot_cluster_distribution(df_rel, outdir)
    plot_subcluster_heatmap(df_rel, outdir)
    plot_venue_cloud(df_rel, outdir)
    plot_interrelation_chord(df_rel, outdir)

    print("\n[✔] All plots and counts generated successfully.")


if __name__ == "__main__":
    main()
