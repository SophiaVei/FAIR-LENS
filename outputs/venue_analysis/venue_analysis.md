# FAIR-LENS venue-structure analysis

This report analyzes the 340 directionally relevant unique papers used for RQ1. It supplements, rather than replaces, the manuscript's top-10 venue figure.

## Corpus-level venue dispersion

- Directionally relevant unique papers: **340**
- Distinct venue labels: **259**
- Papers in the most frequent venue: **15** (4.41%)
- Papers in the top 10 venues combined: **61** (17.94%)
- Singleton venues (one paper): **224 venues**, covering **224 papers** (65.88% of papers)

### Long tail

| long_tail_bin | n_venues | share_of_venues_pct | n_papers | share_of_papers_pct |
| --- | --- | --- | --- | --- |
| 1 paper | 224 | 86.49 | 224 | 65.88 |
| 2 papers | 20 | 7.72 | 40 | 11.76 |
| 3-5 papers | 11 | 4.25 | 38 | 11.18 |
| 6-10 papers | 2 | 0.77 | 12 | 3.53 |
| >10 papers | 2 | 0.77 | 26 | 7.65 |

## Broad venue groups

Venue names were mapped to coarse publication-community groups using transparent name-based rules. The complete mapping is exported in `venue_group_mapping.csv`.

| venue_group | n_papers | n_venues | share_of_papers_pct |
| --- | --- | --- | --- |
| Engineering / Computer Science | 116 | 86 | 34.12 |
| Other / Unclassified | 82 | 74 | 24.12 |
| Biomedical / Health | 37 | 31 | 10.88 |
| General AI / ML / Data Mining | 37 | 27 | 10.88 |
| Multidisciplinary / General Science | 24 | 4 | 7.06 |
| NLP / Computational Linguistics | 19 | 14 | 5.59 |
| Education / Social Science / Other Applied | 12 | 12 | 3.53 |
| Information Systems / Data / Digital Society | 7 | 5 | 2.06 |
| Responsible AI / HCI / Ethics | 6 | 6 | 1.76 |

- Papers currently mapped to `Other / Unclassified`: **82** (24.12%).
- **Manual review recommended:** more than 20% of papers remain unclassified; inspect `venue_group_mapping.csv` before using the grouped distribution in the manuscript.

## Author-normalized venue breadth

For authors with at least two papers in the directionally relevant subset, venue diversity is normalized as `(V_a - 1) / (P_a - 1)`, where `P_a` is the author's number of papers and `V_a` the number of distinct venues. The score is 0 when all of an author's papers appear in one venue and 1 when every paper appears in a different venue. An analogous score is computed for broad venue groups.

- Papers with usable author metadata: **340/340** (100.00%)
- Authors with at least two papers: **32**
- Repeat authors publishing in more than one venue: **19/32** (59.38%)
- Median normalized venue diversity: **1.000** (IQR 0.000--1.000)
- Repeat authors publishing across more than one broad venue group: **11/32** (34.38%)
- Median normalized broad-group diversity: **0.000** (IQR 0.000--1.000)

## Interpretation guardrail

Raw venue-label dispersion should not be interpreted as equivalent to the number of distinct research communities. The grouped venue analysis and author-normalized breadth provide the additional context needed before making claims about interdisciplinarity or community fragmentation.
