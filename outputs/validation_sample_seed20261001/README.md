# FAIR-LENS pathway-coding validation sample

This directory documents the reproducible sampling procedure used for the
manual validation of FAIR-LENS paper--pathway assignments.

## Sample

- Sampling unit: paper--pathway assignment.
- Pathways are used as the six sampling strata.
- 20 positive assignments are sampled without replacement from each pathway.
- Total sampled assignments: 120.
- Unique papers represented: 93.
- Complete positive-assignment frame: 815 assignments from 340 unique papers.
- Fixed random seed: 20261001.

Because FAIR-LENS uses multi-label coding, the same paper can legitimately be
sampled under more than one pathway. The 120 validation cases
therefore correspond to 93 unique papers.

## Reviewer files

Each researcher receives reviewer_1.csv or reviewer_2.csv containing the same
120 sampled paper--pathway assignments.

For every sampled assignment, the sheet contains:

- paper metadata;
- title and abstract;
- the pathway being checked;
- the model-generated justification and directional claim; and
- blank fields for the researcher's assessment and supporting evidence.

The reviewer records whether the sampled pathway assignment is supported,
unsupported, unclear, or unavailable. The reviewer can consult the full text
where the title and abstract are insufficient and can record the relevant
section/page and evidence.

The same paper may appear more than once when it was independently sampled
under more than one pathway. It need not be read from the beginning again, but
each sampled paper--pathway relation is evaluated separately.

## Comparison of judgments

The two researchers' initial judgments should be retained separately.
coordinator/adjudication.csv can then be used to document:

1. whether the researchers initially differed;
2. the final judgment after discussion; and
3. whether that final judgment differs from the original model assignment.

These quantities should not be conflated.

## Reproducibility

coordinator/sampling_frame.csv contains the complete positive-assignment
sampling frame.

coordinator/selected_assignments.csv contains the 120 sampled
assignments.

coordinator/pathway_summary.csv records pathway-specific population sizes,
sampling fractions, and weights.

manifest.json records the seed, input hashes, sampled identifiers, and other
provenance information.

The script generates the sample and review templates only. Human validation
judgments are entered manually.
