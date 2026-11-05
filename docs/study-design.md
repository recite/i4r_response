# I4R citation responses: study design

Revised 2026-11-04. This is a retrospective design, not a preregistration.
Inherited citation outcomes and three-case exploratory estimates have been seen.
This revision follows the decision to study citation trajectories first and
citation contexts second. The prior context-only plan is preserved in
[context-design.md](context-design.md); the older restrictive material-error
specification remains in [i4r/design.md](i4r/design.md).

## Question and comparison

Among I4R-assessed original articles with verified public assessment dates and
adequate observation, how does the change in annual citations compare with
same-journal, same-publication-year research articles? Average original-level
contrasts equally. Report unfavorable, favorable, mixed and unresolved assessments
separately, retaining source definitions. Reproduction, robustness, coding errors
and new-data replications are different assessments, not one pass/fail variable.

The starting population is the full frozen assessment inventory: 590 assessment
units concerning 551 originals. Curated material-error cases are a selected subset,
not the study population. Unresolved assessments remain in the denominator.
Native classifications require an explicit reviewed crosswalk before pooling them.

## Dates and data

Keep the original's publisher date, indexed publication year, report publication
date and earliest substantiated public assessment date separately, with sources
and precision. OSF creation and current catalog publication dates are leads for
review, not verified first disclosure. Date intervals spanning years cannot supply a unique event year. Preserve all original-to-report links.
An earlier individual report takes precedence over a later aggregate announcement;
uncertain chronology stays unresolved. A dated critique of one claim does not
prove it was the first assessment of the original. Review that distinction before
calling the broader analysis an initial-assessment comparison. Repeated assessments
remain linked; one original receives one weight in a given comparison.

End outcomes at 2025, the last complete calendar year. The primary outcome is
unique citing articles/reviews per original/year, with complete incoming-link
retrieval and DOI deduplication (stable OpenAlex ID when no DOI exists). Cached OpenAlex annual totals across all types
are a separately labeled provisional measurement. Never mix these measurements
within a comparison, and never replace an unavailable year with zero. Preserve
source receipts, snapshot dates and acquisition failures. No bulk replication
packages are needed.

## Windows, controls and estimation

The main balanced window is three complete years before and three after the
assessment, omitting the event year. A separately labeled short-window diagnostic
uses two years before and the first full year after. Three post years through 2025 require an event in 2022 or earlier. It is not a substitute for
missing long-run evidence. Require publication before the first baseline year.
For conservative eligibility, a partial publication date must unambiguously
precede that year. Also show annual paths and the number of contributing originals.

Use exact journal and indexed publication year consistently for both arms.
Use a complete census where available or an explicitly labeled seeded sample of up to 20 candidates from the journal/year pool; never substitute the API's default first page. Exclude known assessed originals,
items retracted before or during the event year and documented nonresearch items; report the limits of the screen.
Later retractions remain in the main donor pool and are flagged for a sensitivity excluding them. Undated known retractions remain ineligible. Do not silently widen to adjacent years. Within the eligible pool, select up to
five nearest donors using standardized log(1 + annual citations) in baseline
years, with equal coordinate weights and deterministic identity tie-breaking.
Use donor-pool population standard deviations; omit constant coordinates. If all
coordinates are constant, retain their tied distances and select deterministically,
flagging that the citation histories cannot distinguish donors. Export matching distances to 12 decimal places for cross-platform stability;
selection uses the full computed precision. No post-event citations enter selection. Missing baseline data for an otherwise eligible donor
blocks matching; missing post-data for a selected donor blocks the contrast rather
than causing replacement. Report distances, levels, slopes and donor reuse. Report per-coordinate differences in baseline log citations and whether the original falls outside the donor range; do not present a poor match as evidence of comparable counterfactual trends. Retain such cases as descriptive diagnostics rather than choosing a result-dependent caliper.

Each case contrast is its mean post-minus-pre citation change minus the same
change averaged across its selected donors. Summaries weight originals equally.
Report cases and raw paths before aggregate estimates. A future proportional
model is a distinct estimand; log(1 + citations) differences are not percentages.

The current executable diagnostic uses the earliest verified *curated challenge*
per original. It does not restrict to material errors, but this convenience subset
is still selected. It reports descriptive contrasts only, not a general I4R effect
or a completed first-assessment analysis. A reviewed chronology and assessment
crosswalk are required to extend it to the full population.

## Interpretation and uncertainty

A causal interpretation requires comparable untreated trends, no anticipatory
response, no differential coincident news and limited spillovers. Selection into
replication and the delay between writing and publication can violate these.
Check earlier held-out pre-years where available; matching-year fit is not an
independent test. Examine original-publication timing, later assessments,
mechanical citations from replication reports, author self-citations, donor
contamination, alternative baselines and influential cases. Do not select a
specification because its estimate agrees with prior literature or expectations.

For the small cached diagnostic, report individual contrasts without inferential
p-values or a population causal interval. Before broader estimation, map shared
reports/programs and reused donors, then implement and test inference preserving
those dependencies. Report cluster counts and leave-report-out sensitivity.
Precision and minimum detectable effects remain to be assessed on that map;
absence of significance will not establish absence of a meaningful response.
The predefined primary outcome/window is article/review counts over three pre
and three post years. Other windows and measurements are sensitivity analyses.

## Second stage: citation contexts

After the basic panel, draw a small deterministic probability sample of citing
works within originals and pre/post periods, retaining sampling probabilities. Sample from the complete citation frame before checking text access; retain inaccessible sampled works.
Retrieve available full texts with URLs, hashes and version dates. Extract every
in-text citation to the original with surrounding paragraphs and reference-entry
linkage. A bibliography mention or failed extraction is not an approving citation.

Give an LLM judge the extracted passages plus the dated finding/assessment packet.
Code separately: use of the challenged finding; approving/supportive, critical or
neutral use; explicit concern or qualification; correction uptake; explicit defense;
and unaffected-method/result use. Preserve mixed uses and unjudgeable cases.
Require quoted evidence and passage offsets for each judgment. A lack of concern
in an extracted paragraph does not establish absence elsewhere in the paper.

Use the citing work as the unit, retaining all passages. Code any challenged-finding use and any substantive concern, plus mixed stance when passages disagree. Estimate each period share with sampling weights and compare pre/post shares within originals before averaging across originals. Concern before disclosure may reflect independent criticism; it is not awareness of a future assessment. Separate
all-citation shares from shares conditional on using the challenged finding. Review
a small calibration set manually and with an independent model, retain initial
ratings and disagreements, then evaluate the revised codebook on new cases. Keep
model/version/prompt records. Report access and extraction coverage and sensitivity
to missing texts. Publication after a challenge does not establish that the
manuscript was written afterward. The existing 49-work post-only queue is an access
pilot, not a before/after sample. No LLM-judged outcome has yet been produced.

## Review and changes

An independent model reviewed the revised design and executable diagnostic on
2026-11-04. Changes made before interpreting new comparisons: preserve the full
roster independently of eligibility; state the 2022-or-earlier cutoff for three
post years; retain later-retracted donors and flag them; expose baseline support;
use stable IDs when citing DOIs are absent; reject inconsistent event dates;
record the complete pool used for each comparison. The conservative annual rule
excludes a donor retracted during the event year when ordering is unresolved.

The same review clarified second-stage sampling before text-access filtering,
work-level aggregation of multiple passages, sampling weights, and the distinction
between pre-existing criticism and awareness of an assessment. This review is not
independent re-adjudication of the underlying I4R reports.

## Historical replication expansion

The historical extension uses the pinned FLoRA roster in `data/expansion/`.
Its exposure is the earliest recorded journal-publication year of a replication
report, verified against Crossref metadata. It does not establish the first
public disclosure of results. Select chronology from all recorded replication
attempts before filtering by outcome or observation window. Combine reports in
the same first year; conflicting outcomes remain mixed. An earlier or same-year
unverified report blocks that chronology. Preserve earlier reproduction/I4R and
later-assessment flags. One original receives one weight per window.

Estimate the publication response separately for source-coded successful and
failed replications, and their difference. Source outcome criteria vary and are
not independent adjudications of every finding. Original document types other
than research articles and mismatched titles require review. Exclude known
assessed originals and assessment reports from controls; missing publisher
metadata, flagged nonresearch items and currently flagged retractions are
ineligible in this extension. The current-retraction restriction differs from the
older I4R rule and may exclude some later-retracted papers.

Keep the existing three-before/three-after primary window and the separately
reported two-before/one-after window. Match up to five donors on pre-period
citations from fixed seeded journal/year samples of 20. A missing baseline in an
otherwise eligible donor blocks the comparison; a missing selected follow-up
does not trigger replacement. Counts are OpenAlex citing article/review works,
using individually filtered queries and complete year-bin reconciliation.
The attempted reference-ID/year batching optimization failed an independent
single-target count check and is not used.

Change-score WLS with case fixed effects assigns weight one to each original
and total weight one to its donors. The successful and failed coefficients must
numerically equal the corresponding means of the original-level contrasts.
Two-way paper/report clustering accounts for reused donors and shared reports;
connected same-year report bundles share a cluster. Use fixest's nonnested
parameter correction, cluster correction and minimum-cluster t degrees of
freedom. Do not repair a non-positive-semidefinite covariance silently. These
intervals condition on the matches and classifications; they do not capture
uncertainty in source coding or all potentially shared project influences.

Report donor support, report concentration, control reuse and held-out pre-period
changes. Sensitivities omit the largest report, later assessments in the outcome
window, prior other assessments, or targets outside the candidate pool's baseline
range. Those exclusions change the population. The difference of the two ATTs
uses their joint covariance; it is not the causal effect of failing rather than
succeeding, because replication outcomes are not randomly assigned.
