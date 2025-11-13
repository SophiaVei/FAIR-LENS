#!/usr/bin/env python3
"""
Triangle Insights Visualization

Generates publication trends and descriptive analytics
from the triangle LLM screening outputs.

Inputs:
    - outputs/tri_results_master.csv (required)
    - outputs/tri_results_Q1.csv ... Q6.csv (optional for details)

Outputs:
    - outputs/plots/triangle_trends.html / .png
    - outputs/plots/cluster_distribution.html / .png
    - outputs/plots/subcluster_heatmap.png
    - outputs/plots/venues_top.html / .png
    - outputs/plots/venues_top_papers.md   <-- papers per top venue (unique)
    - outputs/plots/venues_all.csv         <-- ALL venues + counts (unique)
    - outputs/plots/venues_all.md          <-- human-readable version
    - outputs/plots/triangle_sunburst.html

Run:
    python triangle_insights.py --input outputs/tri_results_master.csv
"""

import argparse
import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap

# -----------------------
# Global aesthetic setup
# -----------------------

# Light, modern background
PLOT_BG_COLOR = "#FFFFFF"   # warm light beige
PAPER_BG_COLOR = "#FFFFFF"  # white
GRID_COLOR = "#E0D9CC"      # soft warm gray
TEXT_COLOR = "#1F2933"      # dark slate
FONT_FAMILY = "DejaVu Sans"  # safe cross-platform font

# Earthy qualitative palette for Q1–Q6 (and other discrete categories)
QUAL_6 = [
    "#386641",  # deep olive
    "#A98467",  # warm brown
    "#6C757D",  # slate gray
    "#B56576",  # dusty rose
    "#A3B18A",  # sage
    "#D4A373",  # sand
]

# Earthy pastel qualitative palette for clusters
PASTEL_10 = [
    "#C9D6B8",  # soft sage
    "#F2C6A0",  # light terracotta
    "#E8D9B5",  # pale sand
    "#C7B8EA",  # muted lavender
    "#F3B5B3",  # blush
    "#B0C4B1",  # muted green
    "#F6DFAE",  # light mustard
    "#D8B4A0",  # clay
    "#D5E2C6",  # very soft sage
    "#E3C1D3",  # dusty pink
]

# Continuous scale for counts (bars etc.) – warm, earthy blues/greens
CONTINUOUS_EARTH = ["#F5ECE3", "#C9D6B8", "#8FB996", "#386641"]


sns.set_theme(
    style="white",
    context="talk",
    rc={
        "axes.edgecolor": GRID_COLOR,
        "axes.labelcolor": TEXT_COLOR,
        "xtick.color": TEXT_COLOR,
        "ytick.color": TEXT_COLOR,
        "text.color": TEXT_COLOR,
        "axes.titlesize": 18,
        "axes.labelsize": 14,
        "xtick.labelsize": 12,
        "ytick.labelsize": 12,
    },
)


# -----------------------
# Helpers
# -----------------------

def clean_venue(raw: str) -> str | None:
    """
    Lightly normalize the venue field so that the 'Top venues' plot
    is meaningful. We try to:
      - strip country/extra info in parentheses
      - standardize a few common names
      - drop obvious publisher/noise-only strings
      - drop very long noisy descriptions
    """
    if pd.isna(raw):
        return None

    v = str(raw).strip()
    if not v:
        return None

    # 1) Remove parenthetical content like "(Basel, Switzerland)"
    v = re.sub(r"\(.*?\)", "", v).strip()

    # 2) Remove leading descriptors like "Published in", "In:"
    v = re.sub(r"^(published in|in:|in )\s+", "", v, flags=re.IGNORECASE)

    # 3) Normalize whitespace
    v = re.sub(r"\s+", " ", v).strip()

    # 4) Standardize some common venues/journals
    replacements = {
        "plos one": "PLOS ONE",
        "plos one ": "PLOS ONE",
        "ieee access": "IEEE Access",
        "scientific reports": "Scientific Reports",
        "cureus": "Cureus",
    }
    low = v.lower()
    if low in replacements:
        v = replacements[low]

    # 5) Drop very long noisy entries (likely full descriptions)
    if len(v) > 120:
        return None

    # 6) Drop obvious publisher/platform names used alone
    garbage_keywords = [
        "springer", "elsevier", "mdpi", "arxiv", "biorxiv",
        "nature portfolio", "nature publishing", "preprint"
    ]
    if any(g in v.lower() for g in garbage_keywords):
        return None

    # 7) Too short or generic → drop
    if len(v) < 4:
        return None

    return v


# -----------------------
# Data loading
# -----------------------

def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    # keep only LLM-relevant items (post-screening)
    df = df[df["relevant"] == True]

    # clean venues for plotting
    df["venue_clean"] = df["venue"].apply(clean_venue)

    return df


# -----------------------
# Plot styling helper
# -----------------------

def style_plotly_figure(
    fig,
    title: str,
    x_title: str,
    y_title: str,
    legend_title: str | None = None,
    width: int = 1000,
    height: int = 600,
    legend_orientation: str = "h",
    legend_at_bottom: bool = True,
):
    """
    Apply consistent, beautiful styling to a plotly figure.
    By default, legend is placed at the bottom to avoid overlapping with the title.
    """

    # legend placement
    if legend_at_bottom:
        legend_y = -0.18 if legend_orientation == "h" else 0.5
        legend_yanchor = "top" if legend_orientation == "h" else "middle"
    else:
        legend_y = 1.02
        legend_yanchor = "bottom"

    fig.update_layout(
        title=dict(
            text=title,
            x=0.5,
            xanchor="center",
            yanchor="top",
        ),
        plot_bgcolor=PLOT_BG_COLOR,
        paper_bgcolor=PAPER_BG_COLOR,
        font=dict(
            family=FONT_FAMILY,
            size=16,
            color=TEXT_COLOR,
        ),
        width=width,
        height=height,
        margin=dict(l=70, r=40, t=90, b=110 if legend_at_bottom else 70),
        xaxis=dict(
            title=x_title,
            showgrid=True,
            gridcolor=GRID_COLOR,
            zeroline=False,
        ),
        yaxis=dict(
            title=y_title,
            showgrid=True,
            gridcolor=GRID_COLOR,
            zeroline=False,
        ),
        legend=dict(
            title=legend_title,
            orientation=legend_orientation,
            yanchor=legend_yanchor,
            y=legend_y,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor=GRID_COLOR,
            borderwidth=1,
            itemclick="toggleothers",
            itemdoubleclick="toggle",
        ),
    )
    return fig


# -----------------------
# Plots
# -----------------------

def plot_yearly_trends(df: pd.DataFrame, outdir: Path):
    """One line per question (Q1–Q6)."""
    df_trend = df.copy()

    # Clean question id: keep only "Q1"..."Q6" from any messy value
    df_trend["qid"] = (
        df_trend["question_id"]
        .astype(str)
        .str.extract(r'^(Q[1-6])', expand=False)
    )

    # Drop rows without valid year or qid
    df_trend = df_trend[df_trend["year"].notna() & df_trend["qid"].notna()]

    # Aggregate counts per year & question
    trend = (
        df_trend.groupby(["qid", "year"])
        .size()
        .reset_index(name="count")
        .sort_values(["qid", "year"])
    )

    # Legend labels
    q_labels = {
        "Q1": "Q1 (F→E)",
        "Q2": "Q2 (E→F)",
        "Q3": "Q3 (F→LLMs)",
        "Q4": "Q4 (LLMs→F)",
        "Q5": "Q5 (E→LLMs)",
        "Q6": "Q6 (LLMs→E)",
    }
    trend["Question"] = trend["qid"].map(q_labels).fillna(trend["qid"])

    fig = px.line(
        trend,
        x="year",
        y="count",
        color="Question",
        markers=True,
        color_discrete_sequence=QUAL_6,
    )

    # Styling for lines and markers
    fig.update_traces(
        line=dict(width=3),
        marker=dict(
            size=9,
            line=dict(width=1.5, color=PAPER_BG_COLOR),
        ),
        hovertemplate="<b>%{fullData.name}</b><br>Year: %{x}<br>Count: %{y}<extra></extra>",
    )

    fig = style_plotly_figure(
        fig,
        title="Yearly Publication Trends per Question",
        x_title="Publication Year",
        y_title="Number of Papers",
        legend_title="Question",
        legend_at_bottom=True,   # keep titles clear
    )

    html_path = outdir / "triangle_trends.html"
    fig.write_html(html_path)
    fig.write_image(outdir / "triangle_trends.png", scale=2)
    print(f"[PLOT] Saved yearly trends → {html_path}")


def plot_cluster_distribution(df: pd.DataFrame, outdir: Path):
    cluster_counts = df.groupby("cluster").size().reset_index(name="count")

    fig = px.bar(
        cluster_counts,
        x="cluster",
        y="count",
        color="cluster",
        text="count",
        color_discrete_sequence=PASTEL_10,
    )

    fig.update_traces(
        textposition="outside",
        marker=dict(
            line=dict(color="#D5CCBD", width=1.2),
        ),
        hovertemplate="<b>%{x}</b><br>Count: %{y}<extra></extra>",
    )

    fig = style_plotly_figure(
        fig,
        title="Relevant Papers per Cluster",
        x_title="Cluster",
        y_title="Number of Papers",
        legend_title="Cluster",
        legend_at_bottom=True,
    )

    fig.update_layout(
        xaxis=dict(
            title="Cluster",
            showgrid=False,
            tickangle=0,
        ),
        yaxis=dict(
            title="Number of Papers",
            showgrid=True,
            gridcolor=GRID_COLOR,
        ),
    )

    fig.write_html(outdir / "cluster_distribution.html")
    fig.write_image(outdir / "cluster_distribution.png", scale=2)
    print(f"[PLOT] Saved cluster distribution → {outdir / 'cluster_distribution.html'}")


def plot_subcluster_heatmap(df: pd.DataFrame, outdir: Path):
    heat = df.groupby(["cluster", "subcluster"]).size().reset_index(name="count")
    pivot = heat.pivot(index="cluster", columns="subcluster", values="count").fillna(0)

    # Custom warm, earthy colormap
    cmap = LinearSegmentedColormap.from_list(
        "tri_heat",
        ["#FFFFFF", "#F2C6A0", "#C9D6B8", "#8FB996", "#386641"],
    )

    plt.figure(figsize=(14, 7))
    ax = sns.heatmap(
        pivot,
        annot=True,
        fmt=".0f",
        cmap=cmap,
        cbar=True,
        cbar_kws={"shrink": 0.85, "pad": 0.02},
        linewidths=0.5,
        linecolor=GRID_COLOR,
        square=False,
        annot_kws={"size": 11, "color": TEXT_COLOR},
    )

    ax.set_title("Subcluster Density Heatmap", pad=18, fontsize=18, fontweight="bold")
    ax.set_xlabel("Subcluster", fontsize=14)
    ax.set_ylabel("Cluster", fontsize=14)

    plt.xticks(rotation=35, ha="right")
    plt.yticks(rotation=0)

    ax.set_facecolor(PLOT_BG_COLOR)
    plt.tight_layout()
    plt.savefig(outdir / "subcluster_heatmap.png", dpi=220)
    plt.close()
    print(f"[PLOT] Saved subcluster heatmap → {outdir / 'subcluster_heatmap.png'}")


def plot_venue_cloud(df: pd.DataFrame, outdir: Path):
    """
    Use a de-duplicated view so that each (paper, venue) pair
    is counted only once, even if the paper is relevant to
    multiple questions.
    """
    # Restrict to rows with a cleaned venue
    df_venue = df[df["venue_clean"].notna()].copy()

    # De-duplicate by paper identity at that venue
    df_venue_unique = df_venue.drop_duplicates(
        subset=["title", "year", "venue_clean", "url"]
    )

    # -------- ALL venues + counts (unique papers) --------
    all_venue_counts = (
        df_venue_unique["venue_clean"]
        .value_counts()
        .reset_index()
    )
    all_venue_counts.columns = ["venue", "venue_count"]

    total_unique_venues = len(all_venue_counts)

    # Save as CSV
    venues_all_csv = outdir / "venues_all.csv"
    all_venue_counts.to_csv(venues_all_csv, index=False)

    # Save as Markdown
    lines = []
    lines.append("# All Venues (unique-paper counts)\n")
    lines.append(f"- Total unique venues: **{total_unique_venues}**\n")
    lines.append("\n| # | Venue | Number of Papers |\n|---|-------|------------------|\n")
    for i, row in all_venue_counts.reset_index().iterrows():
        idx = i + 1
        v = str(row["venue"])
        c = int(row["venue_count"])
        lines.append(f"| {idx} | {v} | {c} |")
    venues_all_md = outdir / "venues_all.md"
    venues_all_md.write_text("\n".join(lines), encoding="utf-8")

    print(f"[VENUES] Saved ALL venues → {venues_all_csv} and {venues_all_md}")

    # -------- TOP-15 venues plot --------
    venue_counts = all_venue_counts.head(15).copy()

    fig = px.bar(
        venue_counts,
        x="venue_count",
        y="venue",
        orientation="h",
        color="venue_count",
        color_continuous_scale=CONTINUOUS_EARTH,
    )

    fig.update_traces(
        marker=dict(
            line=dict(color="#D5CCBD", width=1.2),
        ),
        hovertemplate="<b>%{y}</b><br>Count: %{x}<extra></extra>",
    )

    fig = style_plotly_figure(
        fig,
        title="Top 15 Venues for Relevant Papers (Unique Papers)",
        x_title="Number of Papers",
        y_title="Venue",
        legend_title=None,
        legend_at_bottom=False,  # coloraxis legend is off anyway
    )

    fig.update_layout(
        coloraxis_showscale=False,
        yaxis=dict(
            categoryorder="total ascending",
            showgrid=False,
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor=GRID_COLOR,
        ),
        legend=dict(visible=False),
    )

    fig.write_html(outdir / "venues_top.html")
    fig.write_image(outdir / "venues_top.png", scale=2)
    print(f"[PLOT] Saved venue distribution → {outdir / 'venues_top.html'}")

    # -------- write a Markdown file listing all unique papers per top venue --------
    top_venues = venue_counts["venue"].tolist()
    df_top = df_venue_unique[df_venue_unique["venue_clean"].isin(top_venues)].copy()

    # sort for nicer reading
    df_top = df_top.sort_values(["venue_clean", "year", "title"])

    md_lines: list[str] = []
    md_lines.append("# Papers per Top Venue\n")
    md_lines.append(
        "This file lists all **unique** papers for the venues shown "
        "in the 'Top 15 Venues' plot.\n"
    )

    for venue in top_venues:
        sub = df_top[df_top["venue_clean"] == venue]
        md_lines.append(f"\n## {venue} ({len(sub)} papers)\n")
        for _, row in sub.iterrows():
            year = int(row["year"]) if not pd.isna(row["year"]) else "NA"
            title = str(row["title"]).strip()
            url = str(row["url"]).strip() if pd.notna(row["url"]) and row["url"] else ""
            if url:
                md_lines.append(f"- **{year}** — {title}  \n  {url}")
            else:
                md_lines.append(f"- **{year}** — {title}")

    md_path = outdir / "venues_top_papers.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"[LIST] Saved detailed (unique) paper list per top venue → {md_path}")


def plot_interrelation_chord(df: pd.DataFrame, outdir: Path):
    """Visualize cluster ↔ direction hierarchy as sunburst."""
    pairs = df.groupby(["cluster", "subcluster"]).size().reset_index(name="count")

    fig = px.sunburst(
        pairs,
        path=["cluster", "subcluster"],
        values="count",
        color="cluster",
        color_discrete_sequence=PASTEL_10,
    )

    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>Count: %{value}<extra></extra>",
        insidetextorientation="radial",
    )

    fig = style_plotly_figure(
        fig,
        title="Hierarchical Relationships Between Clusters and Directions",
        x_title="",
        y_title="",
        legend_title="Cluster",
        width=800,
        height=800,
        legend_at_bottom=True,
    )

    # For sunburst, axes titles are not meaningful; hide them
    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=10, r=10, t=90, b=110),
    )

    fig.write_html(outdir / "triangle_sunburst.html")
    print(f"[PLOT] Saved cluster hierarchy → {outdir / 'triangle_sunburst.html'}")


# -----------------------
# Main
# -----------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--input",
        type=str,
        default="outputs/tri_results_master.csv",
        help="Path to master CSV.",
    )
    ap.add_argument(
        "--outdir",
        type=str,
        default="outputs/plots",
        help="Output directory for plots.",
    )
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Loading data from {args.input}")
    df = load_data(Path(args.input))

    plot_yearly_trends(df, outdir)
    plot_cluster_distribution(df, outdir)
    plot_subcluster_heatmap(df, outdir)
    plot_venue_cloud(df, outdir)
    plot_interrelation_chord(df, outdir)

    print("\n[✔] All plots generated successfully in:", outdir)


if __name__ == "__main__":
    main()
