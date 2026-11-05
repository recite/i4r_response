# I4R assessment responses: retrospective study plan

Written 2026-11-04. Status: feasibility, not preregistered confirmation. The
inherited three-case citation results, two-case synthetic comparisons, registry
coverage, and native classifications have already been examined. New context
ratings have not yet been collected. Record amendments before changing the queue
or coding rules; later changes remain visible in Git.

## Question and estimand

The immediate pilot is restricted to the 38 inherited curated assessment records,
which can bundle several claims. It is not drawn from all 590 enumerated assessment
units. Among those bundles with verified material consequences and at least one
complete post-disclosure year, test whether we can measure the share of subsequent
article/review citing works that use the affected claim without qualification,
qualify or correct it, explicitly defend it, or use only unaffected material.
The initial window is the first full calendar year after first substantiated
public disclosure; exclude the disclosure year. Average within original article,
then across originals equally. The pilot's `assessment_id` identifies a claim
bundle, not an atomic claim. Split bundles into versioned `claim_id` records with
dated scope before estimating claim-level shares. A citing work counts once per
original in original-level shares; report whether it uses any affected claim and
retain mixed/contradictory uses. Claim-level shares are separate and cannot be
pooled by counting the same citing work repeatedly as independent evidence.

This is initially a descriptive quantity for eligible assessed originals with
complete citation acquisition. No probability sample of all scientific papers
exists. Report the attrition from catalog listings to assessments, originals,
verified claims, timing eligibility, citation completeness, and accessible full text.
Never equate an unobserved outcome with a favorable assessment or zero citations.
The current pilot does not estimate prevalence for all verified errors in I4R.
An original with zero citing works has an undefined use share; report its zero
citation count separately and exclude it from averages of use shares. The eventual
share denominator is all verified citing works for an original with at least one,
including uses of unaffected material; a separate conditional share among affected
claim users answers a different question and must be labeled accordingly.

## Distinctions that must survive construction

- Original articles, independent assessment teams, versions, assessed claims,
  disclosure events, and citing works are separate entities with stable IDs.
- Computational reproduction, demonstrated coding/data/inference error,
  robustness sensitivity, and new-data replication are different assessments.
- Favorable, unfavorable, mixed, disputed, and unresolved judgments retain their
  source definitions. A nonsignificant reanalysis is not automatically an error.
- Record corrected magnitude/direction, whether the affected claim is central,
  and whether a correction strengthens or weakens it. No universal prediction
  that every correction should reduce citations follows.
- Author replies, agreement, journal corrections, and later assessments are
  outcomes or subsequent events. They are not automatic baseline controls.

Dates require evidence that the relevant result was publicly available. An upload,
catalog appearance, original report date, and publication of an aggregate overview
are not interchangeable. Preserve precision and earlier-version uncertainty.
The 2026 Nature overview does not reset earlier individual report dates.

Every candidate needs a dated evidence packet establishing which particular
claim and correction were public before the sampled citing work. The queue marks
this temporal review pending. Do not use later additions to a critique, replies,
or retractions to classify what an earlier citation should have acknowledged.
For example, the inherited dp_294 record distinguishes later 2026 criticisms from
its 2021 disclosure; dp_226 includes expanded criticisms and a 2025 retraction.
Split their scopes and dates before coding. Preserve the citing version's date,
including earlier preprints where available. Publication after disclosure does
not establish that the citing text was written after disclosure. Report that
chronological limitation and any first-public-version sensitivity explicitly.

## Measurement before expansion

`scripts/feasibility.py` constructs a fixed seed sample of up to five first-post-year
citing article/review works per eligible claim with complete cached acquisition.
The inclusion probability is min(5, N)/N within claim. All other eligibility and
missingness states stay in the roster. This queue is a measurement pilot;
five texts per claim cannot support precise case-level prevalence estimates.

Two independent readers inspect the relevant original claim, assessment and
reply, then code citing text under [the protocol](context-review.md). Retain
separate initial judgments and adjudication. This independent-reader requirement
is not satisfied by two prompts to one model. Automated extraction can locate
passages; inferred sentiment alone cannot establish reliance.

Before expansion, report access coverage by case and year, ambiguous/uncodable
rates, the reader confusion matrix, raw agreement and a chance-adjusted measure,
and examples of disagreements. The question is whether the distinction is stable
enough to change an interpretation, not whether a single reliability threshold
can be passed. Check whether agreement persists on newly sampled texts after
revising the codebook; do not evaluate revised rules only on their training cases.

## Broader comparison and identification

Only after source/date review supports it, compare claim-use distributions across
material-error, limited-error, robustness, new-data and favorable assessments.
Use a complete predefined I4R program where possible; the current mixed catalog
is not a randomized sample, nor evidence of random assignment to assessors.
Selection into a replication game, manuscript availability, and publication of
negative reports can all be selective. Preserve program, team and version links.

The primary extension remains descriptive. Standardizing by field, article age,
pre-disclosure citations and report year changes the target population; specify
those weights before observing the new coded outcomes. Neither matching nor
event-time plots establish that the disclosure caused the observed response.

Citation-count contrasts are secondary. Keep equal-original additive changes
separate from model-based proportional estimates. A causal interpretation would
require credible untreated citation paths, no anticipation, appropriate treatment
timing and limited spillovers. Examine held-out pre-periods, publicity/positive-news
comparisons, donor contamination and report-level dependence. Do not pool the
old three-case comparison as a general I4R effect or use already treated articles
as untreated controls in a conventional staggered fixed-effects regression.

## Missingness, inference and sensitivity

Accessible text is not necessarily representative of all citing works. Record
retrieval failures and unresolved linkage; report worst-case bounds that assign
missing texts to each extreme outcome. Acquisition completeness refers to a
provider snapshot and does not prove universal bibliographic coverage. Keep
article/review links distinct from OpenAlex all-type precomputed annual totals.

For the pilot, report counts and within-claim sampling probabilities without a
population causal interval. For a larger descriptive sample, account for sampling
within originals, shared reports, repeated citing works and multiple assessed
claims; finalize the variance model after mapping those dependencies and before
estimating new outcome contrasts. A large number of citation pairs does not imply
many independent disclosure events. Assess precision/power using the observed
cluster structure and pilot coding rates before expanding acquisition; no MDE
has yet been established.

Predeclared diagnostics include claim-use versus generic favorability, report
co-citation versus substantive correction uptake, explicit defenses, unaffected
claims within the same original, later assessments, date uncertainty, mechanical
citations from assessment reports, and self/assessment-author citations. These
are interpretation checks, not randomly assigned placebos. Record report and
author identities before estimating exclusions. Report uncertainty and changing
denominators by horizon rather than selecting a favorable post period.

## Decision and next work

Proceed with measurement feasibility and date/classification audit. Do not launch
paid or bulk acquisition on the strength of this pilot alone. Scale if reliable
claim-specific measurement and adequate case diversity/follow-up survive review.
Narrow or stop if the only defensible finding is the already known persistence of
citations, if access makes the target quantity uninformative, or if assessment
families cannot be compared without conflating incompatible outcomes.

The closest prior work includes context analysis, not only citation counts; see
[prior-work.md](prior-work.md). Any claimed novelty must be updated against those
studies before manuscript drafting.
