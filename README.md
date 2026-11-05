# Responses to replication assessments

Do citations change after a study is replicated, and does the response differ
between successful and failed replications? This repository links replication
reports to original papers, follows their annual citations, and compares changes
with papers from the same journal and publication year.

The [current results](docs/historical-results.md) are preliminary. The historical
sample extends beyond the Institute for Replication (I4R), using the FORRT Library
of Reproduction and Replication Attempts (FLoRA). Collection is incomplete, some
originals have poor comparison matches, and pre-period trends weaken a causal
interpretation. Citation counts measure attention, not agreement.

## Reproduce the results

This is a research repository, not an installable Python package. Download a
[release](https://github.com/recite/i4r_response/releases) or clone the repository:

```sh
git clone https://github.com/recite/i4r_response.git
cd i4r_response
uv sync --locked
uv run --locked make check
make restore-r
uv run --locked make check-r
```

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), R, and Make
first. Python 3.13 and R 4.6.0 are the tested runtimes. Python dependencies are
locked in `uv.lock`; R dependencies are pinned in `renv.lock`. Dependency
installation needs network access. All analysis checks then run from committed
inputs without API credentials or the local source cache.

`make check` runs Black, isort, flake8, Python tests, registry reconstruction,
coverage checks and citation matching. `make check-r` reproduces the inherited
I4R comparisons and historical success/failure estimates, then runs R tests and
lintr. To rebuild only the historical estimates after installing dependencies:

```sh
uv run --locked make historical historical-r
```

## Read and use the data

Start with the [study design](docs/study-design.md),
[historical results](docs/historical-results.md), and
[historical data guide](data/expansion/README.md). The
[I4R coverage report](docs/trajectory-results.md) describes the separate I4R
inventory and timing limitations. [Prior work](docs/prior-work.md) explains how
this study relates to existing research.

The analysis uses the first recorded journal-publication year of a replication
report. That date need not be the first public disclosure. Success and failure
are source classifications, with varying criteria; failure need not apply to
every finding in a paper. Matching uses only pre-report citation histories.
Intervals account for shared reports and reused controls, conditional on the
matches and classifications. The difference between the two response estimates
is not the causal effect of a replication failing rather than succeeding.

The inherited [three-case comparison](docs/i4r/aggregate-results.md) and
[synthetic-control checks](docs/i4r/synthetic-results.md) remain available. Their
outcomes were examined before the broader design was written. The
[migration record](docs/migration.json) identifies code and data separated from
[`sig_fault`](https://github.com/recite/sig_fault). Citation collection also adapts
methods from [`propagation_of_error`](https://github.com/recite/propagation_of_error).

## Extend collection

Acquisition is separate from the offline analysis:

```sh
uv run scripts/replication_metadata.py --fetch
uv run scripts/replication_collect.py pools --fetch
uv run scripts/replication_collect.py histories --fetch
```

OpenAlex collection requires an API key in `OPENALEX_API_KEY` or
`~/.config/openalex/api_key`. History collection defaults to zero prepaid spend;
`--max-paid-usd` sets an explicitly authorized cumulative prepaid cap. Metadata
and pool acquisition do not share that guard, so check your available API budget
before running them. Cached responses allow resumption. Request URLs, retrieval
dates and checksums are retained; credentials are not written to receipts.

The source roster is pinned in `data/expansion/source_snapshots.csv`.
`uv run scripts/replication_sources.py fetch` retrieves those CSV snapshots using
`gh`; `build` reconstructs the candidate roster. See the
[source guide](docs/i4r/README.md) for the earlier I4R collection. Completed
citation years end in 2025; partial 2026 counts are excluded. The I4R source
catalog ends on 2026-10-05, while FLoRA uses its separately pinned revision.

A later stage will examine whether citing papers rely on challenged findings or
acknowledge concerns. The [context protocol](docs/context-review.md) specifies
that work; no LLM-judged citation-context result is included in this release.
Bulk replication datasets and environments are unnecessary: keep source
references and retrieve only documents needed for a specific check. See the
[cache policy](docs/cache-policy.md).

## Attribution and reuse

Code is available under the [MIT license](LICENSE). Data sources and their terms
are documented in [DATA_SOURCES.md](DATA_SOURCES.md), including FLoRA's CC BY 4.0
license. Third-party text retains its source rights. Cite this repository using
[CITATION.cff](CITATION.cff), and credit the source datasets when reusing their
records. [Release notes](CHANGELOG.md) distinguish completed work from outstanding
collection and design questions.
