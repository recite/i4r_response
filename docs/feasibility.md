# I4R response: feasibility audit

Decision: **narrow and test**. Citation persistence alone is not a new contribution.
The candidate extension measures whether subsequent authors use the specific
challenged claim, qualify it, or use an unaffected part of the original article.
This requires new full-text assessment; no such result is reported here.

| Stage | Count |
|---|---:|
| Frozen catalog listings | 714 |
| Enumerated assessment units | 590 |
| Distinct originals in those assessments | 551 |
| Resolved assessment units | 365 |
| Unresolved assessment units | 225 |
| Curated claim-bundle records | 38 |
| Bundles passing initial identity/date/materiality screens | 15 |
| Candidate originals | 15 |
| Complete cached histories | 11 |
| Bundles represented in the review queue | 11 |
| Sampled bundle–citing-work pairs | 49 |
| Completed citation-context ratings | 0 |

The catalog was frozen on 2026-10-05; citation follow-up ends in 2025. Recent
assessments are not failures and do not supply completed 2026 outcomes.
The descriptive context sample needs one full post year; it does not impose
the inherited causal-comparison requirement for several baseline years.

The queue selects up to five unique article/review citing works per candidate
bundle in the first full calendar year after disclosure, using a fixed hash seed.
It includes only originals with complete cached citation acquisition. Selection
probabilities are saved. Bundles must be split into dated atomic claims before
claim-level inference. A completed history with no citing works is zero;
an incomplete or missing history has a blank count. Queue pairs are not
independent observations when they share an original, report, or citing work.
This is a feasibility sample, not an estimate for the entire I4R catalog.

All candidate claim packets still require temporal review: later replies or
expanded critiques cannot be applied to citations that preceded them. Initial
materiality/date screens are not evidence that the as-of packet is ready.

Native assessment labels are retained in `data/feasibility/native_dispositions.csv`.
They have not been collapsed into success/failure. Date and claim-level evidence
are much less complete than the assessment inventory. Positive, robustness, and
new-data assessment groups need consistent classification and date review before
comparisons can be estimated. Full-text accessibility and reviewer agreement
remain unmeasured. See [design](study-design.md) and [prior work](prior-work.md).
