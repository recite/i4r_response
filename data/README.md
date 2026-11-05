# Data

The binary success/failure analysis uses the FORRT Library of Reproduction and
Replication Attempts (FLoRA). I4R records provide an additional assessment inventory
and identify already assessed papers that should not enter comparison pools.
A source record is not automatically an eligible event or a completed comparison.

## Sources and reuse

| Source | What we use | Attribution and terms |
|---|---|---|
| FLoRA | Original/report links, source outcomes and bibliographic fields | Wallrich, Röseler and colleagues (2026), [FLoRA](https://doi.org/10.17605/OSF.IO/9R62X), [CC BY 4.0](https://forrt.org/replication-hub/flora/). |
| OpenAlex | Work identities, journals and citation histories | [OpenAlex database](https://help.openalex.org/data/how-its-built/), CC0. |
| Crossref | Publisher dates, types, titles and DOI checks | [Crossref terms](https://www.crossref.org/documentation/retrieve-metadata/#licensing): factual metadata are unrestricted; abstracts retain source copyright. |
| I4R and RePEc | Report inventory, evidence and publication references | Source URLs and retrieval receipts are in `raw/i4r/`; reports and quoted passages retain their original rights. |
| Earlier I4R coding | Computational, robustness and materials scores | [recite/i4replication](https://github.com/recite/i4replication); exact revision in `raw/replications/source_snapshots.csv`. |

The source snapshot table records revisions, URLs, checksums and retrieval dates.
FLoRA fields are selected and DOI strings normalized; publication verification
and eligibility screens are our additions. We preserve source outcome labels
rather than interpreting them as verdicts on every finding. The source providers
have not endorsed or independently validated this analysis.

Our original annotations and numerical outputs are available under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Third-party text,
including abstracts and evidence excerpts, retains its source rights and is not
covered by the project's MIT or CC BY grants. Full papers, replication packages,
credentials and private working caches are not distributed.

## Reading the tables

`raw/replications/` contains source inputs. The main files are:

- `flora_candidates.csv`: original/report links and source outcome classifications.
- `metadata.csv`: DOI and publisher-date verification for originals and reports.
- `comparison_pools.csv`, `comparison_members.csv`, `comparison_articles.csv`:
  seeded samples of up to 20 papers per journal/year and their identities.
- `comparison_exclusions.csv`: control exclusions, including reviewed nonresearch items.
- `citations.csv`: annual counts of citing OpenAlex article/review works.
- `citation_totals.csv`: collection status, count reconciliation and receipts.
- `metadata_sources.csv`: metadata request URLs, retrieval dates and checksums.
- `prior_i4r_labels.csv`: prior report-level scores with unresolved mappings retained.

`raw/i4r/` contains the source inventory and curated evidence, original-paper
identities, disclosure records and previously collected histories. These are
research inputs, not separate three-paper or synthetic-control results.

`../tabs/` contains the current generated analysis:

| Table | Row unit |
|---|---|
| `events.csv` | Original paper and its first recorded replication-report event |
| `event_links.csv` | Original/report link used to establish chronology |
| `eligibility.csv` | Original/window combination and reasons it is available or excluded |
| `matches.csv` | Selected original/control/window match and distance |
| `cases.csv` | Original/window contrast and matching-support diagnostics |
| `changes.csv` | Original or control within a matched comparison |
| `estimates.csv` | Window, outcome and sensitivity specification, with uncertainty |
| `paths.csv`, `balance.csv`, `dependence.csv` | Annual paths, baseline differences and shared-report/control dependence |

`five_year` matches on five pre-report years and measures change over the last
three pre-report and first three post-report years. `three_year` uses three complete calendar years before and three after the report;
`short` uses two before and one after. All omit the report year and stop in 2025.
`article_id` identifies the original in a comparison; `control_id` identifies a
selected control. In the stacked `changes.csv`, `paper_id` identifies the physical
paper and `case_id` the comparison. Reused papers retain their identifiers.

`candidate_for_matching` means an event passed its screen. `contrast_available`
means the complete comparison can be calculated. `budget_stop` means a requested
history was not collected under the spending cap; it never means zero citations.
Missing source values remain missing, and duplicate keys or inconsistent year
counts stop the analysis.

`design_*.csv` report matching-history coverage, estimates on available and common
samples, and held-out pre-report validation. Generated LaTeX tables and
macros feed the research note directly.
