# Citation-context study

After the citation-count analysis, sample citing works before and after an
assessment to ask whether they use the challenged finding as evidence and whether
they acknowledge a concern. No completed ratings are available.

Select the sample before checking full-text availability. Preserve inclusion
probabilities and inaccessible works. Date each claim packet using only evidence
publicly available before the citing work; later replies must not contaminate
earlier judgments. Sample both periods and keep repeated assessments explicit.

For each claim/citing-work pair, retain two reader records with these fields:

| Field | Allowed values / meaning |
|---|---|
| claim_id, citing_work_id, reader_id | Composite key; retain parent assessment_id; never substitute title-only matching |
| fulltext_status | retrieved / unavailable / pending |
| reference_verified | yes / no / uncertain |
| claim_relevance | affected_claim / unaffected_material_only / both / unclear |
| use_role | evidential_support / magnitude_or_calibration / method_or_data / background / criticism / mixed / unclear |
| qualification | none / acknowledges_uncertainty / adopts_correction / explicit_defense / mixed / unclear |
| assessment_acknowledged | yes / no / unclear; separate from whether its bibliography entry exists |
| original_and_corrected_claim | Evidence-backed paraphrase identifying what changed |
| evidence_locator | Section/page/paragraph for each judgment |
| evidence_excerpt | Minimum necessary passage; keep copyrighted full text private |
| notes | Ambiguity, multiple mentions, or conflicting passages |

Derive mutually exclusive original–citing-work outcomes only after adjudication:

1. **Unaffected use only:** no use of an affected claim; includes unaffected methods,
   data, and background references.
2. **Unqualified substantive use:** affected claim supplies evidence, a magnitude,
   or calibration, with no qualification anywhere relevant in the text.
3. **Qualified/corrected use:** affected claim is used with uncertainty or the
   documented correction, without incompatible unqualified use elsewhere.
4. **Explicit defense:** the critique is addressed and the original affected claim
   is affirmatively defended; do not label this lack of awareness.
5. **Criticism/rejection only:** affected claim is discussed to criticize or reject it.
6. **Affected-claim mention without substantive reliance:** historical/background
   discussion or attribution, with no evidential or calibration use.
7. **Mixed:** incompatible uses remain across mentions or claims in one paper.
8. **Uncodable:** text is inaccessible, relevance unclear, or temporal scope unresolved.

Verify the reference link first. A false database link is a linkage error outside
the citing-work denominator, reported separately. Uncertain links remain unresolved;
report denominator bounds with them included and excluded rather than dropping them. An unavailable but verified link
remains in that denominator with a missing outcome. Report category shares over
all verified citing works and missing-outcome bounds. A background mention with
`qualification=none` is category 6, not category 2. Originals with zero verified
citing works have no defined share. The pilot produces reliability/availability
diagnostics, not stable estimates of these shares.

Read all relevant mentions before a paper-level judgment. A favorable reference to
an unaffected method is not unqualified reliance on the corrected result. A paper
that defends the original after discussing the critique is not unaware of it.
Assess correction direction and substantive scope before coding what reliance
would mean. Do not classify authors' intent or claim the underlying study is
universally false.

Store initial reader records unchanged, then a separate adjudication table with
both initial values and a reason. Lack of accessible text remains missing; do not
code the abstract as if the full paper were read. Do not replace inaccessible
sampled works with convenient available ones. A replacement wave requires a new
sampling record and inclusion probabilities.
