#!/usr/bin/env python3
"""Freeze a reproducible FAIR-LENS positive-assignment audit sample.

Run from the repository root (Python 3.9+, standard library only):
    python scripts/sample_validation_assignments.py

Inputs: outputs/tri_results_Q1.csv ... outputs/tri_results_Q6.csv.
These are the complete relevant-only exports produced by questions.py.
Sampling does not perform human validation or modify any existing coding.
"""

import argparse
import csv
import hashlib
import io
import json
import platform
import random
import re
import subprocess
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

VERSION = "1.0.0"
DEFAULT_SEED = 20261001  # Fixed before inspecting the first sample.
PATHWAYS = {
    "Q1": ("RP1", "Explanation Requirements", "Fairness -> Explainability",
           "Fairness or bias concerns motivate, shape, or define explanation requirements for transparency, contestability, recourse, and accountability."),
    "Q2": ("RP2", "Fairness Evidence", "Explainability -> Fairness",
           "XAI or explanation methods are used to examine fairness problems, including bias, unfairness, proxy effects, identity cues, or uneven outcomes."),
    "Q3": ("RP3", "Fairness Specification", "Fairness -> LLMs",
           "Fairness or bias principles define, adapt, or operationalize criteria for LLM evaluation, benchmark construction, design, alignment, monitoring, or deployment."),
    "Q4": ("RP4", "Fairness Impacts", "LLMs -> Fairness",
           "LLM behavior or outputs are assessed as evidence of fairness-related outcomes, including bias, refusals, omissions, toxicity, harms, or unequal quality of service."),
    "Q5": ("RP5", "Model Behavior", "Explainability -> LLMs",
           "XAI or interpretability methods are applied to inspect LLM behavior, including prompts, outputs, tokens, retrieved context, representations, activations, or internal mechanisms."),
    "Q6": ("RP6", "Explanation Mediation", "LLMs -> Explainability",
           "LLMs support explanation practices by generating, translating, summarizing, evaluating, mediating, or producing natural-language explanations and rationales."),
}
META = ["title", "year", "venue", "url", "abstract"]
MISSING = {"", "nan", "none", "null", "n/a", "<na>"}


def clean(value):
    value = str(value or "").strip()
    return "" if value.casefold() in MISSING else value


def normalized_title(title):
    return " ".join(unicodedata.normalize("NFKC", title).casefold().split())


def paper_key(row):
    title = normalized_title(clean(row.get("title")))
    if not title:
        raise ValueError("A record has no title; resolve its identity before sampling.")
    year = clean(row.get("year"))
    if year and not re.fullmatch(r"\d{4}(?:\.0+)?", year):
        raise ValueError("Invalid publication year: " + repr(year))
    year = year.split(".")[0]
    return json.dumps([title, year], ensure_ascii=False, separators=(",", ":"))


def paper_id(key):
    return "P-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:20]


def load_pools(input_dir):
    """Reject malformed or duplicate assignments rather than altering the frame."""
    pools, provenance, papers, warnings = {}, [], {}, []
    ids = {}
    for qid in PATHWAYS:
        source = Path(input_dir) / ("tri_results_" + qid + ".csv")
        raw = source.read_bytes()
        if raw.startswith(b"version https://git-lfs.github.com/spec/"):
            raise ValueError(str(source) + " is a Git LFS pointer, not a CSV.")
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
        required = {"question_id", "relevant", "title", "year"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(str(source) + " lacks required columns: " + str(sorted(required)))
        pool = {}
        for record_number, row in enumerate(reader, 1):
            if None in row or any(row.get(k) is None for k in required):
                raise ValueError(f"Malformed CSV record {record_number} in {source}")
            if clean(row["question_id"]) != qid:
                raise ValueError(f"Unexpected question_id in {source}, record {record_number}")
            if clean(row["relevant"]).casefold() not in {"true", "1", "yes"}:
                raise ValueError(f"{source} must contain positive assignments only; record {record_number} does not.")
            key = paper_key(row)
            if key in pool:
                raise ValueError(f"Duplicate paper-pathway assignment in {source}: {row['title']}. Resolve before sampling.")
            pid = paper_id(key)
            if pid in ids and ids[pid] != key:
                raise ValueError("Paper identifier collision; increase identifier length.")
            ids[pid] = key
            item = {field: clean(row.get(field)) for field in META}
            item["year"] = item["year"].split(".")[0]
            item.update(paper_id=pid, paper_key=key, question_id=qid,
                        source_file=source.name, source_record=record_number,
                        model_reason=clean(row.get("reason")),
                        model_claim=clean(row.get("directional_claim")))
            pool[key] = item
            if key not in papers:
                papers[key] = {k: item[k] for k in ["paper_id"] + META}
            else:
                for field in ["venue", "url", "abstract"]:
                    old, new = papers[key][field], item[field]
                    if old and new and " ".join(old.split()) != " ".join(new.split()):
                        warnings.append(f"Metadata differs across exports for {pid}: {field}. Check sources; no record excluded.")
                    elif not old and new:
                        papers[key][field] = new
        pools[qid] = pool
        provenance.append({"file": source.name, "bytes": len(raw),
                           "sha256": hashlib.sha256(raw).hexdigest(), "positive_assignments": len(pool)})
    return pools, papers, provenance, sorted(set(warnings))


def pathway_seed(seed, qid):
    text = f"FAIR-LENS-positive-audit-v1|{seed}|{qid}"
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16)


def select_assignments(pools, per_pathway, seed):
    """Simple random sampling without replacement, independently in each stratum."""
    if per_pathway < 1:
        raise ValueError("--per-pathway must be at least 1.")
    selected = {}
    for qid in PATHWAYS:
        keys = sorted(pools[qid])  # Selection does not depend on CSV row order.
        if len(keys) < per_pathway:
            raise ValueError(f"{qid} has {len(keys)} assignments; cannot select {per_pathway} without replacement.")
        rng = random.Random(pathway_seed(seed, qid))
        selected[qid] = sorted(rng.sample(keys, per_pathway))
    return selected


def write_csv(path, fields, rows):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def local_git_commit(input_dir):
    try:
        result = subprocess.run(["git", "-C", str(Path(input_dir).resolve()), "rev-parse", "HEAD"],
                                capture_output=True, text=True, timeout=5, check=True)
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def export_sample(input_dir, outdir, per_pathway=20, seed=DEFAULT_SEED, source_ref=None):
    outdir = Path(outdir)
    if outdir.exists():
        raise ValueError(f"Output directory already exists: {outdir}. Use a NEW directory; existing audits are never overwritten.")
    pools, papers, sources, warnings = load_pools(input_dir)
    selected = select_assignments(pools, per_pathway, seed)
    chosen = sorted(set().union(*(set(keys) for keys in selected.values())))
    membership = {(qid, key) for qid, keys in selected.items() for key in keys}
    sample_rows, frame_rows, strata = [], [], []
    for qid, pool in pools.items():
        rp, name, direction, _ = PATHWAYS[qid]
        size = len(pool)
        strata.append({"question_id": qid, "pathway": rp, "name": name,
                       "population_assignments": size, "sample_assignments": per_pathway,
                       "inclusion_probability": per_pathway / size,
                       "assignment_weight": size / per_pathway})
        for key in sorted(pool):
            row = dict(pool[key], pathway=rp, pathway_name=name, direction=direction,
                       assignment_id=pool[key]["paper_id"] + "-" + qid,
                       selected_primary=int((qid, key) in membership),
                       inclusion_probability=per_pathway / size, assignment_weight=size / per_pathway)
            frame_rows.append(row)
            if (qid, key) in membership:
                sample_rows.append(row)

    blind_rows, code_rows, paper_rows = [], [], []
    for key in chosen:
        paper = papers[key]
        paper_rows.append(dict(paper))
        for qid, (rp, name, direction, _) in PATHWAYS.items():
            base = {k: paper[k] for k in ["paper_id", "title", "year", "venue", "url"]}
            base.update(question_id=qid, pathway=rp, pathway_name=name, direction=direction)
            blind_rows.append(base)  # No model code, rationale, or sampling-stratum flags.
            original = pools[qid].get(key, {})
            code_rows.append(dict(base, selected_primary=int((qid, key) in membership),
                                  exported_positive=int(key in pools[qid]),
                                  model_reason=original.get("model_reason", ""),
                                  model_claim=original.get("model_claim", "")))

    # Only create output files after input and sampling checks succeed.
    (outdir / "coordinator").mkdir(parents=True, exist_ok=False)
    reviewer_dir = outdir / "reviewers"
    reviewer_dir.mkdir()
    frame_fields = ["assignment_id", "paper_id", "question_id", "pathway", "pathway_name", "direction",
                    "title", "year", "venue", "url", "source_file", "source_record",
                    "selected_primary", "inclusion_probability", "assignment_weight"]
    write_csv(outdir / "coordinator/sampling_frame.csv", frame_fields, frame_rows)
    write_csv(outdir / "coordinator/selected_assignments.csv", frame_fields + ["model_reason", "model_claim"], sample_rows)
    write_csv(outdir / "coordinator/pathway_summary.csv", list(strata[0]), strata)
    write_csv(reviewer_dir / "papers_for_review.csv", ["paper_id"] + META, paper_rows)
    review_fields = ["paper_id", "title", "year", "venue", "url", "question_id", "pathway", "pathway_name", "direction",
                     "human_label", "reading_scope", "full_text_url", "evidence_location", "evidence_excerpt",
                     "rationale", "reviewer", "review_date"]
    for reviewer in (1, 2):
        write_csv(reviewer_dir / f"reviewer_{reviewer}.csv", review_fields, blind_rows)
    adjudication_fields = review_fields[:9] + ["selected_primary", "exported_positive", "model_reason", "model_claim",
                                              "reviewer_1_label", "reviewer_2_label", "initial_human_disagreement",
                                              "final_label", "differs_from_export", "error_type",
                                              "evidence_location", "resolution_notes"]
    write_csv(outdir / "coordinator/adjudication.csv", adjudication_fields, code_rows)
    codebook = [{"question_id": qid, "pathway": rp, "name": name, "direction": direction, "definition": definition}
                for qid, (rp, name, direction, definition) in PATHWAYS.items()]
    write_csv(reviewer_dir / "pathway_definitions.csv", list(codebook[0]), codebook)

    report = {
        "script_version": VERSION, "created_utc": datetime.now(timezone.utc).isoformat(),
        "audit_status": "sample_selected_human_review_not_performed_by_script",
        "design": "equal-allocation stratified simple random sampling without replacement of positive assignments",
        "stratification_variable": "question_id", "seed": seed, "per_pathway": per_pathway,
        "rng": "Python random.Random (MT19937), sample() over sorted normalized title-year keys",
        "stratum_seed_derivation": "SHA256(FAIR-LENS-positive-audit-v1|<seed>|<question_id>), interpreted as an integer",
        "python_version": platform.python_version(), "python_implementation": platform.python_implementation(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "source_ref_supplied": source_ref, "local_git_commit": local_git_commit(input_dir),
        "input_directory": str(Path(input_dir).resolve()), "input_files": sources,
        "paper_identity": "NFKC-normalized, casefolded, whitespace-collapsed title plus normalized year; inherits upstream bibliographic deduplication",
        "population_assignments": len(frame_rows), "population_unique_papers": len(papers),
        "selected_assignments": len(sample_rows), "selected_unique_papers": len(chosen),
        "review_sheet_rows_per_reviewer": len(blind_rows),
        "missing_abstracts_in_selected_papers": sum(not p["abstract"] for p in paper_rows),
        "missing_urls_in_selected_papers": sum(not p["url"] for p in paper_rows),
        "pathways": strata,
        "selected_assignment_ids": [r["assignment_id"] for r in sample_rows],
        "selected_paper_ids": [papers[key]["paper_id"] for key in chosen],
        "warnings": warnings,
    }
    instructions = f"""# FAIR-LENS revision audit: selected sample

Status: the script selected a sample. No human judgments or validation results have been generated.

- Seed: {seed}; {per_pathway} positive assignments per pathway.
- Selected assignments: {len(sample_rows)}; unique papers: {len(chosen)}.
- Sampling frame: {len(frame_rows)} positive assignments from {len(papers)} unique papers.
- Each researcher receives {len(blind_rows)} blank paper-pathway rows: all six pathways for each selected paper.

## Review workflow

1. Freeze this directory and the codebook before reviewing. Keep the seed and selected cases;
   do not reroll or replace papers because they look difficult, incorrect, or inaccessible.
2. Give each researcher only the reviewers folder and their own reviewer_N.csv.
   Its sheets omit model predictions, rationales, and which pathways triggered selection.
   This reduces exposure; it cannot undo prior knowledge of the coding.
3. Read papers in full where accessible. In human_label enter yes, no, unclear, or unavailable.
   In reading_scope enter full_text, title_abstract, or unavailable. Record page/section evidence,
   rationale, reviewer name and date. Never treat unavailable as no. For missing URLs search by title.
   Unavailable/unclear cases stay in the sample and must be reported.
4. Assess all six pathways for each paper, including opposite directions. This permits detection
   of missing labels within sampled positive papers. Apply definitions to what the study actually
   does; a term or a model-generated rationale is not sufficient evidence. Record ambiguities.
5. Preserve both researchers' initial files before discussion. Then use the coordinator folder
   to compare judgments and document final decisions in adjudication.csv; do not overwrite initial labels.
   exported_positive=0 means absent from the complete positive exports, not a new human negative decision.
6. Report the {len(sample_rows)} selected_primary=1 cases separately from extra checks on other
   pathways in these same papers. Distinguish human-human disagreements, human-model differences,
   and final coding corrections. A corrected assignment remains in the original audit sample.

## Scope and analysis

The unit is a paper-pathway assignment. Strata are pathways, not years or venues. Draws are
independent across pathways; a paper can legitimately be selected in several of them. Read it
once per researcher but retain its separate sampled assignments. No quality/venue/year filter
or forced removal of cross-pathway overlaps is applied.

Equal allocation oversamples the smaller pathways. Per-pathway sampling fractions and weights
are in coordinator/pathway_summary.csv. For an overall positive-assignment confirmation estimate,
use sum(N_q * confirmation_rate_q) / sum(N_q), not the unweighted fraction over 120 cases.
This assumes comparable ascertainment; separately disclose unclear/unavailable cases. Assignments
sharing a paper are dependent, so uncertainty calculations must respect clustering and the design.
The script intentionally computes no accuracy, agreement statistic, or confidence interval.

Twenty is the requested audit budget per pathway, not a power-derived guarantee. This sample
does not estimate corpus-wide recall or validate the 225 entirely negative papers or eligibility
exclusions. Additional all-six-pathway checks on these papers are not a random sample of all
negative assignments. Keep any targeted investigation of known problems separate from this sample.
The review does not, by itself, establish the completeness or validity of the framework.

The included codebook transcribes the current manuscript's pathway definitions. Preserve its
version; document any later clarification and reassess affected cases rather than changing criteria
to preserve the original counts. Freeze input files: hashes are in manifest.json. If the source
frame changes, document a new audit version. Never present this new sample as the original audit.

## Reporting

sampling_method.tex describes ONLY the selection just performed. Add human procedures and
outcomes after completing and recording them. Keep the original audit and this revision audit
distinct in the manuscript. Input CSVs and all earlier analysis outputs are unchanged.
"""
    (outdir / "README.md").write_text(instructions, encoding="utf-8")
    latex = (
        "% Selection completed; human review outcomes must be added only after the audit.\n"
        "\\textcolor{red}{For an additional validation audit during revision, we selected "
        f"{per_pathway} positively coded paper--pathway assignments from each of the six pathways "
        "using stratified random sampling with equal allocation. Within each pathway, assignments "
        "were sampled without replacement from the complete positive-assignment export, using "
        f"a fixed random seed ({seed}). Sampling was performed independently across pathways, "
        "allowing the same paper to be selected under more than one pathway. The resulting sample "
        f"comprised {len(sample_rows)} assignments from {len(chosen)} unique papers. The sampled identifiers, "
        "input-file hashes, and sampling parameters were retained for reproducibility.}\n"
    )
    (outdir / "sampling_method.tex").write_text(latex, encoding="utf-8")
    report["output_sha256_at_generation"] = {
        str(p.relative_to(outdir)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(outdir.rglob("*")) if p.is_file()
    }
    (outdir / "manifest.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--outdir", type=Path, help="Must not exist; default outputs/validation_sample_seed<seed>")
    parser.add_argument("--per-pathway", type=int, default=20)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--source-ref", help="Optional source commit/tag for provenance; file hashes remain authoritative")
    args = parser.parse_args()
    outdir = args.outdir or Path("outputs") / f"validation_sample_seed{args.seed}"
    try:
        result = export_sample(args.input_dir, outdir, args.per_pathway, args.seed, args.source_ref)
    except (OSError, ValueError, csv.Error) as exc:
        parser.exit(2, f"ERROR: {exc}\n")
    print(f"Selected {result['selected_assignments']} assignments from {result['selected_unique_papers']} unique papers.")
    for row in result["pathways"]:
        print(f"  {row['pathway']}: {row['sample_assignments']}/{row['population_assignments']} positive assignments")
    print(f"Seed: {args.seed}. Outputs: {outdir.resolve()}")
    print("Human review remains to be completed. See README.md and reviewers/.")
    if result["warnings"]:
        print(f"Metadata warnings: {len(result['warnings'])}; inspect manifest.json.")


if __name__ == "__main__":
    main()

