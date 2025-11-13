#!/usr/bin/env python3
"""
Triangle Insights Visualization (Enhanced Aesthetic Version)

Generates publication trends and descriptive analytics
from the triangle LLM screening outputs—same functionality
as the simple version, but with significantly improved visuals.

Inputs:
    - outputs/tri_results_master.csv

Outputs:
    - outputs/plots/triangle_trends.html / .png
    - outputs/plots/cluster_distribution.html / .png
    - outputs/plots/subcluster_heatmap.png
    - outputs/plots/venues_top.html / .png
    - outputs/plots/triangle_sunburst.html
"""

import argparse
from pathlib import Path

import pandas as pd
import plotly.express as px
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap


# -----------------------
# GLOBAL AESTHETICS
# -----------------------

# White backgrounds everywhere
PLOT_BG = "#FFFFFF"
PAPER_BG = "#FFFFFF"
GRID_COLOR = "#E3E0DB"
TEXT_COLOR = "#1F2933"

# Earthy tones for categorical plots
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
    }
)


# -----------------------
# DATA LOADING
# -----------------------
def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df[df["relevant"] == True]
    return df


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
        )
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
        marker=dict(size=9, line=dict(width=1.2, color="white"))
    )

    fig = style_plotly(
        fig,
        "Yearly Publication Trends per Question",
        "Publication Year",
        "Number of Papers"
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
        "Number of Papers"
    )

    fig.write_html(outdir / "cluster_distribution.html")
    fig.write_image(outdir / "cluster_distribution.png", scale=2)
    print("[PLOT] Saved cluster distribution")


def plot_subcluster_heatmap(df: pd.DataFrame, outdir: Path):
    pivot = (
        df.groupby(["cluster", "subcluster"]).size()
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
        "Venue"
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
        ""
    )

    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=30, r=30, t=100, b=30)
    )

    fig.write_html(outdir / "triangle_sunburst.html")
    print("[PLOT] Saved sunburst plot")


# -----------------------
# MAIN
# -----------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=str, default="outputs/tri_results_master.csv")
    ap.add_argument("--outdir", type=str, default="outputs/plots")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(exist_ok=True, parents=True)

    print(f"[INFO] Loading data: {args.input}")
    df = load_data(Path(args.input))

    plot_yearly_trends(df, outdir)
    plot_cluster_distribution(df, outdir)
    plot_subcluster_heatmap(df, outdir)
    plot_venue_cloud(df, outdir)
    plot_interrelation_chord(df, outdir)

    print("\n[✔] All plots generated successfully.")


if __name__ == "__main__":
    main()
