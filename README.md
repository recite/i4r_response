# Responses to replication assessments

Do citations to an original study change after a replication or reanalysis becomes
public, compared with papers from the same journal and publication year?

We start with original-publication dates, assessment-publication/disclosure dates,
annual citation histories and matched comparison papers. The full I4R inventory
is the starting population; favorable, unfavorable, mixed and unresolved findings
remain distinct. Citation counts measure attention, not agreement.

**Status: data construction and selected-case diagnostics.** Read the short
[computed status report](docs/trajectory-results.md) and [study design](docs/study-design.md).
The available dates and citation histories do not yet support an I4R-wide conclusion.

A second stage will sample citing papers before and after a challenge, download
available texts, extract citation passages, and use evidence-backed LLM judgments
to distinguish reliance on the challenged finding, concern, correction uptake,
defense and unaffected uses. The existing 49-work post-only queue is an access
pilot, not a before/after result. No LLM-judged outcome has been produced.
See [prior work](docs/prior-work.md) and the [context protocol](docs/context-review.md).

## What is preserved

The registry, evidence reviews, source receipts, acquisition code, matching code,
and numerical tests were separated from [sig_fault](https://github.com/recite/sig_fault).
The [migration record](docs/migration.json) identifies the source commit and file
hashes. Original assessment labels and unresolved cases remain explicit.

The inherited [three-case citation comparison](docs/i4r/aggregate-results.md) and
[synthetic-control checks](docs/i4r/synthetic-results.md) are historical exploratory
results. They are preserved for reproducibility, not evidence that the new study
has succeeded. Their outcomes were already examined before this design was written.
The old restrictive material-error matching design is documented in
[docs/i4r/design.md](docs/i4r/design.md). The new broader roster and exact-year
matching diagnostic are separate outputs in `data/trajectories/`.

`data/i4r/` contains the existing source and assessment registry. Generated coverage
and the deterministic review queue are in `data/feasibility/`. Native reports,
publisher PDFs and API responses are temporary caches in ignored
`private-data/i4r/` locally. They are not distributed on GitHub. Public access does
not establish redistribution rights; original sources retain their own rights. Bulk replication ZIPs were discarded after
receipt verification; see the [cache policy](docs/cache-policy.md).

## Reproduce

Python 3.13 and R 4.6.0 are the tested runtimes. Python dependencies are locked in
`uv.lock`; R dependencies are pinned in `renv.lock`.

```sh
uv sync --locked
uv run --locked make check
make restore-r
uv run --locked make check-r
```

`make check` runs formatting, import sorting, lint, numerical/data-integrity tests,
registry reconstruction, feasibility construction, and citation-trajectory construction. `make check-r` reproduces
the inherited citation comparisons and runs R tests and lint. These builds use
committed inputs and require no source acquisition or private cache.

For a quick standard-library-only feasibility rebuild:

```sh
python3 scripts/feasibility.py
```

Acquisition remains separate and opt-in; see the inherited
[source guide](docs/i4r/README.md). API access, collection costs, and changing
source snapshots must be checked before refreshing. The frozen catalog ends on
2026-10-05 and completed citation years end in 2025. A partial 2026 is not treated
as a complete outcome year.

## Current priorities

Verify first-public assessment dates across the full roster, review assessment
categories, and complete exact journal/year donor pools and citation histories.
`make trajectories` rebuilds the roster, date-evidence links, citation panel,
matching eligibility and selected-case diagnostics from committed inputs.
The original context feasibility design is preserved in
[docs/context-design.md](docs/context-design.md); its post-only sampling rules
are superseded by the second-stage before/after design.
