# FAIR-LENS revision audit: selected sample

Status: the script selected a sample. No human judgments or validation results have been generated.

- Seed: 20261001; 20 positive assignments per pathway.
- Selected assignments: 120; unique papers: 93.
- Sampling frame: 815 positive assignments from 340 unique papers.
- Each researcher receives 558 blank paper-pathway rows: all six pathways for each selected paper.

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
6. Report the 120 selected_primary=1 cases separately from extra checks on other
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
