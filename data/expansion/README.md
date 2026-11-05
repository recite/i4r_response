# Historical replication data

These tables separate the candidate roster, verified publication events, collected
citation histories and matched comparisons. Row counts at one stage are not the
sample size at the next. Rebuild with `make historical historical-r` from the
repository root after installing dependencies. See [source terms](../../DATA_SOURCES.md).

| Table | Row unit and purpose |
|---|---|
| `flora_candidates.csv` | Source original/report record, retaining source outcomes and timing screens. |
| `prior_i4r_labels.csv` | Previously coded I4R report; scores are not automatically assigned to multiple linked originals. |
| `source_snapshots.csv` | Pinned source file, revision, retrieval date and checksum. |
| `metadata.csv`, `comparison_metadata.csv` | DOI identity and publisher-date checks for originals/reports and controls. |
| `metadata_sources.csv` | Actual metadata request URL and receipt checksum; other tables reference these hashes. |
| `events.csv` | Original paper, first recorded report year, outcome and eligibility reasons. |
| `event_links.csv` | Original/report link used to establish chronology. |
| `comparison_pools.csv`, `comparison_members.csv` | Seeded journal/year sample and its member papers; up to 20 candidates, not a census. |
| `comparison_exclusions.csv` | Candidate control and documented exclusion reasons. |
| `citations.csv` | Paper/year count of citing OpenAlex article or review works. |
| `citation_totals.csv` | Requested history, collection status, count reconciliation and source receipt. |
| `matching_eligibility.csv` | Original/window combination and availability or exclusion reasons. |
| `matches.csv` | Selected original/control/window match and pre-period distance. |
| `case_contrasts.csv` | Original/window change relative to its selected controls. |
| `analysis_changes.csv` | Original or control within a matched comparison; input to clustered R inference. |
| `att_estimates.csv` | Window, sensitivity specification and outcome-specific contrast, with standard error and interval. |
| `balance.csv`, `paths.csv`, `dependence.csv` | Baseline balance, annual paths, shared-report concentration and control reuse. |
| `batch_validation.csv` | Failed batched-query experiment; these counts are not used in the analysis. |
| `collection_cost.json` | Provider-reported account changes and the collection's prepaid cap. |

`article_id` identifies an original or comparison paper; `paper_id` identifies
physical papers in the stacked inference table. `case_id` identifies one
original/window comparison. `report_cluster` connects originals sharing a report,
including connected bundles of reports. A control reused in multiple comparisons
keeps the same `paper_id`.

`successful` and `failed` are source-coded replication outcomes. `mixed` and
unresolved cases stay in the roster but do not enter the binary comparison.
`candidate_for_matching` means the publication event passed its screen; it does
not mean citation collection or matching succeeded. `contrast_available` marks
an available original/window comparison. `budget_stop` means no usable response
was collected under the cap; it never means zero citations.

The `balanced_3pre_3post` window compares three full calendar years before and
three after the report year; `short_2pre_1post` uses two before and one after.
Both omit the report year. Complete follow-up ends in 2025. Each original has
weight one, and its controls have total weight one. Estimates are changes in
citations per original per year relative to those controls. Their causal
interpretation requires assumptions that the current diagnostics do not establish.
