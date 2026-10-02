#!/usr/bin/env python3
"""
analyze_venue_structure.py

Targeted venue-structure analysis for FAIR-LENS Reviewer 2, Comment 10.

Inputs
------
1) outputs/tri_results_master.csv
   - used to identify the 340 directionally relevant unique papers
2) a metadata CSV containing title + authors
   - searched automatically in this order:
       outputs/prefilter_kept.csv
       data/lens/stages/S4_tagged.csv
       data/raw/lens.csv
   - or provide explicitly with --metadata

Outputs
-------
outputs/venue_analysis/
    venue_counts.csv
    venue_long_tail.csv
    venue_group_mapping.csv
    venue_groups.csv
    author_venue_breadth.csv
    venue_analysis.md
    manifest.json

The script is descriptive only. It does not alter the FAIR-LENS coding,
Figure 5, or any source data.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd


DEFAULT_MASTER = Path("outputs/tri_results_master.csv")
DEFAULT_OUTDIR = Path("outputs/venue_analysis")
METADATA_CANDIDATES = [
    Path("outputs/prefilter_kept.csv"),
    Path("data/lens/stages/S4_tagged.csv"),
    Path("data/raw/lens.csv"),
]


# ---------------------------------------------------------------------
# Broad venue-community grouping.
# These groups are intentionally coarse. The complete venue -> group
# mapping is exported so it can be inspected and, if necessary, refined.
# ---------------------------------------------------------------------
GROUP_RULES = [
    (
        "NLP / Computational Linguistics",
        [
            r"\bacl\b", r"\bemnlp\b", r"\bnaacl\b", r"\beacl\b", r"\bcoling\b",
            r"\blrec\b", r"\btacl\b", r"computational linguistics",
            r"association for computational linguistics", r"semeval",
            r"natural language processing", r"language resources",
        ],
    ),
    (
        "Responsible AI / HCI / Ethics",
        [
            r"\bfacct\b", r"fairness.*accountability.*transparency",
            r"\baies\b", r"ai ethics", r"ethics and information technology",
            r"responsible ai", r"human[- ]computer", r"\bchi\b", r"\bcscw\b",
            r"\buist\b", r"\btochi\b", r"intelligent user interfaces",
        ],
    ),
    (
        "Biomedical / Health",
        [
            r"medical", r"medicine", r"clinical", r"health", r"biomedical",
            r"bioinformatics", r"npj digital medicine", r"bmc ", r"patient",
            r"radiology", r"oncology", r"psychiatr", r"public health",
            r"healthcare",
        ],
    ),
    (
        "Multidisciplinary / General Science",
        [
            r"scientific reports", r"plos one", r"nature communications",
            r"science advances", r"heliyon", r"frontiers in .*science",
        ],
    ),
    (
        "General AI / ML / Data Mining",
        [
            r"\baaai\b", r"artificial intelligence", r"\bijcai\b",
            r"\bneurips\b", r"neural information processing",
            r"\bicml\b", r"machine learning", r"\biclr\b",
            r"\bkdd\b", r"knowledge discovery", r"data mining",
            r"pattern recognition", r"expert systems",
            r"knowledge-based systems", r"neural computing",
        ],
    ),
    (
        "Engineering / Computer Science",
        [
            r"ieee access", r"\bieee\b", r"\bacm\b", r"computer science",
            r"computing", r"software", r"engineering", r"informatics",
            r"information processing", r"information sciences",
            r"electronics", r"sensors", r"applied sciences",
            r"communications", r"cyber", r"security", r"systems",
        ],
    ),
    (
        "Information Systems / Data / Digital Society",
        [
            r"information systems", r"information management",
            r"information technology", r"information$", r"digital",
            r"decision support", r"data science", r"big data",
            r"internet research",
        ],
    ),
    (
        "Education / Social Science / Other Applied",
        [
            r"education", r"learning", r"social", r"psychology", r"management",
            r"business", r"finance", r"financial", r"law", r"legal",
            r"public administration", r"policy", r"government",
            r"human resources", r"recruit", r"hiring", r"linguistic",
        ],
    ),
]


def norm_space(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def norm_title(value) -> str:
    s = norm_space(value).lower()
    return re.sub(r"[^a-z0-9]+", "", s)


def norm_author(value) -> str:
    s = unicodedata.normalize("NFKD", norm_space(value)).encode("ascii", "ignore").decode()
    s = s.lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def canonical_venue(value) -> str:
    return norm_space(value)


def venue_key(value) -> str:
    return canonical_venue(value).casefold()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def choose_metadata_file(explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit)
        if not p.exists():
            raise FileNotFoundError(f"Metadata file not found: {p}")
        return p

    for p in METADATA_CANDIDATES:
        if p.exists():
            return p

    raise FileNotFoundError(
        "No metadata file with authors was found. "
        "Provide one with --metadata PATH. Expected columns: title, authors."
    )


def categorize_venue(venue: str) -> str:
    text = canonical_venue(venue).lower()
    for group, patterns in GROUP_RULES:
        if any(re.search(p, text, flags=re.I) for p in patterns):
            return group
    return "Other / Unclassified"


def parse_author_item(item) -> str | None:
    if item is None:
        return None

    if isinstance(item, str):
        s = norm_space(item)
        return s or None

    if isinstance(item, dict):
        for key in ("display_name", "full_name", "name", "author_name"):
            if item.get(key):
                return norm_space(item[key])
        first = item.get("first_name") or item.get("given_name") or item.get("given")
        last = item.get("last_name") or item.get("family_name") or item.get("family")
        if first or last:
            return norm_space(f"{first or ''} {last or ''}")

    return norm_space(item) or None


def parse_authors(value) -> list[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []

    if isinstance(value, (list, tuple)):
        out = [parse_author_item(x) for x in value]
        return [x for x in out if x]

    raw = norm_space(value)
    if not raw or raw.lower() == "nan":
        return []

    # Common case: a Python/JSON representation of a list.
    if raw.startswith("[") or raw.startswith("{"):
        for loader in (ast.literal_eval, json.loads):
            try:
                parsed = loader(raw)
                if isinstance(parsed, dict):
                    parsed = parsed.get("authors", parsed.get("data", [parsed]))
                if not isinstance(parsed, (list, tuple)):
                    parsed = [parsed]
                out = [parse_author_item(x) for x in parsed]
                out = [x for x in out if x]
                if out:
                    return out
            except Exception:
                pass

    # FAIR-LENS Lens exports store author display names as comma-separated
    # values ("Given Family, Given Family"). Keep support for alternative
    # separators when an explicitly supplied metadata file uses them.
    for sep in (";", "|", ","):
        if sep in raw:
            return [norm_space(x) for x in raw.split(sep) if norm_space(x)]

    if re.search(r"\s+and\s+", raw, flags=re.I):
        return [norm_space(x) for x in re.split(r"\s+and\s+", raw, flags=re.I) if norm_space(x)]

    return [raw]

def pct(x, denominator) -> float:
    return round(100.0 * x / denominator, 2) if denominator else 0.0



def df_to_markdown(df: pd.DataFrame) -> str:
    """Small dependency-free Markdown table formatter."""
    if df.empty:
        return "_No rows_"
    cols = list(df.columns)
    def fmt(v):
        if pd.isna(v):
            return ""
        return str(v).replace("|", "\\|")
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    rows = [
        "| " + " | ".join(fmt(row[c]) for c in cols) + " |"
        for _, row in df.iterrows()
    ]
    return "\n".join([header, sep] + rows)


def describe_series(series: pd.Series) -> dict:
    if series.empty:
        return {"median": None, "q1": None, "q3": None}
    return {
        "median": round(float(series.median()), 3),
        "q1": round(float(series.quantile(0.25)), 3),
        "q3": round(float(series.quantile(0.75)), 3),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--master", default=str(DEFAULT_MASTER))
    ap.add_argument("--metadata", default=None)
    ap.add_argument("--outdir", default=str(DEFAULT_OUTDIR))
    args = ap.parse_args()

    master_path = Path(args.master)
    outdir = Path(args.outdir)
    metadata_path = choose_metadata_file(args.metadata)

    if not master_path.exists():
        raise FileNotFoundError(f"Master results file not found: {master_path}")

    outdir.mkdir(parents=True, exist_ok=True)

    # -----------------------------------------------------------------
    # 1. Directionally relevant UNIQUE papers
    # -----------------------------------------------------------------
    master = pd.read_csv(master_path)
    required = {"title", "venue", "relevant"}
    missing = required - set(master.columns)
    if missing:
        raise ValueError(f"{master_path} is missing columns: {sorted(missing)}")

    rel = master[master["relevant"].astype(str).str.lower().isin(["true", "1", "yes"])].copy()
    rel["_title_key"] = rel["title"].map(norm_title)
    papers = (
        rel.sort_values(["_title_key", "venue"])
           .drop_duplicates("_title_key")
           [["title", "_title_key", "venue"]]
           .copy()
    )
    papers["venue"] = papers["venue"].map(canonical_venue)
    papers["_venue_key"] = papers["venue"].map(venue_key)

    n_papers = len(papers)

    # -----------------------------------------------------------------
    # 2. Venue counts + long tail
    # -----------------------------------------------------------------
    venue_counts = (
        papers.groupby("_venue_key", dropna=False)
              .agg(
                  venue=("venue", lambda values: sorted(values)[0]),
                  paper_count=("_title_key", "size"),
              )
              .reset_index()
              .sort_values(["paper_count", "venue"], ascending=[False, True])
              .reset_index(drop=True)
    )
    n_venues = len(venue_counts)
    venue_counts["paper_share_pct"] = venue_counts["paper_count"].map(lambda x: pct(x, n_papers))
    venue_counts["venue_group"] = venue_counts["venue"].map(categorize_venue)
    venue_counts.to_csv(outdir / "venue_counts.csv", index=False)

    def tail_bin(c: int) -> str:
        if c == 1:
            return "1 paper"
        if c == 2:
            return "2 papers"
        if 3 <= c <= 5:
            return "3-5 papers"
        if 6 <= c <= 10:
            return "6-10 papers"
        return ">10 papers"

    venue_counts["long_tail_bin"] = venue_counts["paper_count"].map(tail_bin)
    bin_order = ["1 paper", "2 papers", "3-5 papers", "6-10 papers", ">10 papers"]

    tail_rows = []
    for b in bin_order:
        sub = venue_counts[venue_counts["long_tail_bin"] == b]
        tail_rows.append(
            {
                "long_tail_bin": b,
                "n_venues": int(len(sub)),
                "share_of_venues_pct": pct(len(sub), n_venues),
                "n_papers": int(sub["paper_count"].sum()),
                "share_of_papers_pct": pct(sub["paper_count"].sum(), n_papers),
            }
        )
    long_tail = pd.DataFrame(tail_rows)
    long_tail.to_csv(outdir / "venue_long_tail.csv", index=False)

    # -----------------------------------------------------------------
    # 3. Broad venue-group distribution
    # -----------------------------------------------------------------
    venue_mapping = venue_counts[
        ["venue", "paper_count", "paper_share_pct", "venue_group"]
    ].copy()
    venue_mapping["needs_manual_review"] = venue_mapping["venue_group"].eq("Other / Unclassified")
    venue_mapping.to_csv(outdir / "venue_group_mapping.csv", index=False)

    paper_groups = papers.merge(
        venue_counts[["_venue_key", "venue_group"]],
        on="_venue_key",
        how="left",
        validate="many_to_one",
    )
    group_summary = (
        paper_groups.groupby("venue_group")
                    .agg(
                        n_papers=("_title_key", "nunique"),
                        n_venues=("_venue_key", "nunique"),
                    )
                    .reset_index()
    )
    group_summary["share_of_papers_pct"] = group_summary["n_papers"].map(lambda x: pct(x, n_papers))
    group_summary = group_summary.sort_values("n_papers", ascending=False).reset_index(drop=True)
    group_summary.to_csv(outdir / "venue_groups.csv", index=False)

    # -----------------------------------------------------------------
    # 4. Join author metadata back to the 340-paper subset
    # -----------------------------------------------------------------
    metadata = pd.read_csv(metadata_path)
    if "title" not in metadata.columns or "authors" not in metadata.columns:
        raise ValueError(
            f"{metadata_path} must contain 'title' and 'authors' columns. "
            f"Found: {list(metadata.columns)}"
        )

    metadata["_title_key"] = metadata["title"].map(norm_title)
    metadata = (
        metadata.sort_values("_title_key")
                .drop_duplicates("_title_key")
                [["_title_key", "authors"]]
    )

    papers_auth = paper_groups.merge(metadata, on="_title_key", how="left", validate="one_to_one")
    papers_auth["author_list"] = papers_auth["authors"].map(parse_authors)
    papers_with_authors = int(papers_auth["author_list"].map(bool).sum())

    author_rows = []
    for _, row in papers_auth.iterrows():
        for display_name in row["author_list"]:
            author_rows.append(
                {
                    "author": display_name,
                    "author_key": norm_author(display_name),
                    "title": row["title"],
                    "venue": row["venue"],
                    "venue_key": row["_venue_key"],
                    "venue_group": row["venue_group"],
                }
            )

    if author_rows:
        author_papers = pd.DataFrame(author_rows)
        # Deduplicate accidental duplicate author occurrences within the same paper.
        author_papers = author_papers.drop_duplicates(["author_key", "title"])

        author_summary = (
            author_papers.groupby("author_key")
                         .agg(
                             author=("author", "first"),
                             n_papers=("title", "nunique"),
                             n_venues=("venue_key", "nunique"),
                             n_venue_groups=("venue_group", "nunique"),
                         )
                         .reset_index(drop=True)
        )
        repeat = author_summary[author_summary["n_papers"] >= 2].copy()

        if not repeat.empty:
            repeat["venue_diversity_norm"] = (
                (repeat["n_venues"] - 1) / (repeat["n_papers"] - 1)
            ).clip(0, 1)
            repeat["venue_group_diversity_norm"] = (
                (repeat["n_venue_groups"] - 1) / (repeat["n_papers"] - 1)
            ).clip(0, 1)
            repeat["multi_venue"] = repeat["n_venues"] > 1
            repeat["multi_group"] = repeat["n_venue_groups"] > 1
        else:
            repeat["venue_diversity_norm"] = pd.Series(dtype=float)
            repeat["venue_group_diversity_norm"] = pd.Series(dtype=float)
            repeat["multi_venue"] = pd.Series(dtype=bool)
            repeat["multi_group"] = pd.Series(dtype=bool)

        repeat = repeat.sort_values(["n_papers", "n_venues"], ascending=[False, False])
    else:
        repeat = pd.DataFrame(
            columns=[
                "author", "n_papers", "n_venues", "n_venue_groups",
                "venue_diversity_norm", "venue_group_diversity_norm",
                "multi_venue", "multi_group",
            ]
        )

    repeat.to_csv(outdir / "author_venue_breadth.csv", index=False)

    # -----------------------------------------------------------------
    # 5. Compact Markdown report for manuscript / response-letter use
    # -----------------------------------------------------------------
    top10_papers = int(venue_counts.head(10)["paper_count"].sum())
    singleton_row = long_tail[long_tail["long_tail_bin"] == "1 paper"].iloc[0]
    top1_count = int(venue_counts.iloc[0]["paper_count"]) if not venue_counts.empty else 0

    unclassified_papers = int(
        group_summary.loc[
            group_summary["venue_group"] == "Other / Unclassified", "n_papers"
        ].sum()
    )

    venue_div = describe_series(repeat["venue_diversity_norm"]) if not repeat.empty else {}
    group_div = describe_series(repeat["venue_group_diversity_norm"]) if not repeat.empty else {}

    with (outdir / "venue_analysis.md").open("w", encoding="utf-8") as f:
        f.write("# FAIR-LENS venue-structure analysis\n\n")
        f.write("This report analyzes the 340 directionally relevant unique papers used for RQ1. ")
        f.write("It supplements, rather than replaces, the manuscript's top-10 venue figure.\n\n")

        f.write("## Corpus-level venue dispersion\n\n")
        f.write(f"- Directionally relevant unique papers: **{n_papers}**\n")
        f.write(f"- Distinct venue labels: **{n_venues}**\n")
        f.write(f"- Papers in the most frequent venue: **{top1_count}** ({pct(top1_count, n_papers):.2f}%)\n")
        f.write(f"- Papers in the top 10 venues combined: **{top10_papers}** ({pct(top10_papers, n_papers):.2f}%)\n")
        f.write(
            f"- Singleton venues (one paper): **{int(singleton_row['n_venues'])} venues**, "
            f"covering **{int(singleton_row['n_papers'])} papers** "
            f"({float(singleton_row['share_of_papers_pct']):.2f}% of papers)\n\n"
        )

        f.write("### Long tail\n\n")
        f.write(df_to_markdown(long_tail))
        f.write("\n\n")

        f.write("## Broad venue groups\n\n")
        f.write(
            "Venue names were mapped to coarse publication-community groups using transparent "
            "name-based rules. The complete mapping is exported in `venue_group_mapping.csv`.\n\n"
        )
        f.write(df_to_markdown(group_summary))
        f.write("\n\n")
        f.write(
            f"- Papers currently mapped to `Other / Unclassified`: **{unclassified_papers}** "
            f"({pct(unclassified_papers, n_papers):.2f}%).\n"
        )
        if pct(unclassified_papers, n_papers) > 20:
            f.write(
                "- **Manual review recommended:** more than 20% of papers remain unclassified; "
                "inspect `venue_group_mapping.csv` before using the grouped distribution in the manuscript.\n"
            )
        f.write("\n")

        f.write("## Author-normalized venue breadth\n\n")
        f.write(
            "For authors with at least two papers in the directionally relevant subset, "
            "venue diversity is normalized as `(V_a - 1) / (P_a - 1)`, where `P_a` is the "
            "author's number of papers and `V_a` the number of distinct venues. The score is "
            "0 when all of an author's papers appear in one venue and 1 when every paper appears "
            "in a different venue. An analogous score is computed for broad venue groups.\n\n"
        )
        f.write(f"- Papers with usable author metadata: **{papers_with_authors}/{n_papers}** ({pct(papers_with_authors, n_papers):.2f}%)\n")
        f.write(f"- Authors with at least two papers: **{len(repeat)}**\n")
        if not repeat.empty:
            f.write(
                f"- Repeat authors publishing in more than one venue: "
                f"**{int(repeat['multi_venue'].sum())}/{len(repeat)}** "
                f"({pct(int(repeat['multi_venue'].sum()), len(repeat)):.2f}%)\n"
            )
            f.write(
                f"- Median normalized venue diversity: **{venue_div['median']:.3f}** "
                f"(IQR {venue_div['q1']:.3f}--{venue_div['q3']:.3f})\n"
            )
            f.write(
                f"- Repeat authors publishing across more than one broad venue group: "
                f"**{int(repeat['multi_group'].sum())}/{len(repeat)}** "
                f"({pct(int(repeat['multi_group'].sum()), len(repeat)):.2f}%)\n"
            )
            f.write(
                f"- Median normalized broad-group diversity: **{group_div['median']:.3f}** "
                f"(IQR {group_div['q1']:.3f}--{group_div['q3']:.3f})\n"
            )
        else:
            f.write("- No repeat authors could be identified from the available author metadata.\n")

        f.write("\n## Interpretation guardrail\n\n")
        f.write(
            "Raw venue-label dispersion should not be interpreted as equivalent to the number of "
            "distinct research communities. The grouped venue analysis and author-normalized breadth "
            "provide the additional context needed before making claims about interdisciplinarity or "
            "community fragmentation.\n"
        )

    manifest = {
        "script": "analyze_venue_structure.py",
        "master_input": str(master_path),
        "metadata_input": str(metadata_path),
        "master_sha256": sha256_file(master_path),
        "metadata_sha256": sha256_file(metadata_path),
        "directionally_relevant_unique_papers": n_papers,
        "distinct_venue_labels": n_venues,
        "output_directory": str(outdir),
        "outputs": [
            "venue_counts.csv",
            "venue_long_tail.csv",
            "venue_group_mapping.csv",
            "venue_groups.csv",
            "author_venue_breadth.csv",
            "venue_analysis.md",
        ],
    }
    with (outdir / "manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print("[DONE] FAIR-LENS venue analysis")
    print(f"  Papers: {n_papers}")
    print(f"  Venue labels: {n_venues}")
    print(f"  Top-10 papers: {top10_papers} ({pct(top10_papers, n_papers):.2f}%)")
    print(f"  Repeat authors: {len(repeat)}")
    print(f"  Output directory: {outdir}")


if __name__ == "__main__":
    main()

