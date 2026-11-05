# Research design

Estimate how citations change after a replication report, separately for
source-coded successful and failed replications. Compare each original paper's
change with controls from its journal and publication year. The difference of
these two response estimates is not the causal effect of failure versus success:
replication outcomes and the selection of studies for replication are not random.
This is an exploratory observational analysis, not a preregistration.

## Events and outcomes

Start with all FLoRA original/report links. Verify DOIs, titles, article types,
journals and publisher dates using Crossref and OpenAlex. Select the first
recorded journal-report year across all replication attempts before filtering
by outcome or follow-up. Conflicting reports in that year produce a mixed label.
An earlier or same-year unverified report blocks confident chronology. Keep
nonbinary outcomes and exclusions in the roster.

The date is journal publication, not necessarily first public disclosure. A
working paper or public presentation may precede it. Preserve flags for earlier
reproductions, I4R overlap and later assessments. Source success criteria differ;
failure can concern only part of a paper's findings.

Count OpenAlex citing article/review works by publication year, through 2025.
Reconcile every complete annual series with its API total. Missing collection
is not zero. Individually filtered queries are used because a tested batched
reference/year aggregation did not reproduce the individual totals.

## Comparison and estimand

The main window has three full calendar years before and three after the report,
excluding the report year. The shorter window has two before and one after.
Originals and controls must have been published before the first baseline year.
These windows overlap and their sample sizes must not be added.

Use fixed seeded samples of up to 20 candidates from the exact journal and indexed
publication year. Exclude known assessed originals, assessment reports,
nonresearch items, missing publisher metadata, title conflicts and current
retraction flags. This restriction can exclude later-retracted papers; it does
not establish that retained controls were free of every public criticism.

Select up to five controls using mean squared differences in baseline
log(1 + citations), standardized by donor-pool population standard deviations.
Omit constant coordinates. Round distances to ten decimal places and break ties
by paper ID. Post-report citations never enter matching. A missing eligible
control baseline blocks the comparison; missing selected follow-up does not
cause replacement. There is no result-dependent caliper.

For each original, subtract the controls' mean post-minus-pre change from the
original's change. Average these contrasts with equal weight per original,
separately by replication outcome. Counts and changes are in citations per paper
per year, not percentages.

## Uncertainty and diagnostics

Weighted least squares on change scores, with comparison fixed effects, assigns
weight one to each original and total weight one to its controls. Its two outcome
coefficients must reproduce the direct means of the original-level contrasts.
Cluster by physical paper and report: controls can be reused and reports can
cover multiple originals. Connected report bundles share a cluster. Use fixest's
nonnested parameter correction, cluster correction and minimum-cluster t degrees
of freedom. An invalid covariance produces unavailable intervals rather than a
silent repair. Intervals condition on the chosen matches and source labels.

Report baseline levels and log gaps, cases outside their candidate pool's range,
annual paths, control reuse and report concentration. Use the two years preceding
the matching window for a held-out pre-period change comparison where available.
Sensitivities omit the largest report, later assessments in the outcome window,
prior other assessments, or cases outside donor support. Those restrictions
change the population being estimated.

A causal interpretation requires parallel counterfactual trends, no anticipation
and no differential coincident shocks. The current matching and pre-period
diagnostics do not establish those assumptions. Citation counts do not establish
agreement with, or reliance on, a challenged finding.
