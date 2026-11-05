# Responses to replication assessments

Do later researchers use a challenged finding, qualify it, or cite an unaffected
part of the original paper? This study uses the Institute for Replication (I4R)
collection to investigate responses to specific assessments. It distinguishes
demonstrated material errors, limited errors, robustness concerns, new-data
replication results, and favorable assessments.

**Status: feasibility study.** Showing that criticized papers continue to receive
citations is not a new contribution. Prior studies have also examined citation
penalties, acknowledgment, and citation context. The proposed extension is an
auditable link from a particular assessed claim and its corrected interpretation
to how subsequent research uses it. Whether the available cases support a useful
comparison remains to be established.

Start with the [prior-work assessment](docs/prior-work.md),
[study design](docs/study-design.md), and [computed feasibility report](docs/feasibility.md).
The [review protocol](docs/context-review.md) defines the first measurement test.
No new claim-use ratings or causal effects have been estimated.

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
[docs/i4r/design.md](docs/i4r/design.md); it is distinct from the new descriptive
context-review feasibility sample.

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
registry reconstruction, and feasibility construction. `make check-r` reproduces
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

## Next decision

Audit the sampled citing texts with the [coding protocol](docs/context-review.md),
measure full-text access and independent-reader agreement, and finish the
assessment/date crosswalk for comparison groups. Scale collection only if this
produces a reliable, substantive measurement beyond bibliographic co-citation.
The existing `replication_citations` project concerns broader replication-program
citation trajectories; this repository owns the I4R assessment-response study.
