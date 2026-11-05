"""Collect annual article/review counts using propagation_of_error's grouped queries.

Adapted from scripts/openalex_client.py::group_by_year and
scripts/openalex/02_histories.py::pad in recite/propagation_of_error,
commit aba3475109fec6099b91801f4ac9d7149639d78c. Counts are unique OpenAlex
works, not additionally deduplicated by DOI. Fetch and offline build are separate.
"""

from __future__ import annotations

import argparse
import collections
import concurrent.futures
import json
import threading
import urllib.error

import common
import i4r_sources as sources

OUT = sources.DATA / "grouped"
CACHE = sources.CACHE / "grouped_citations"
LAST_YEAR = 2025
CITATION_FIELDS = [
    "article_id",
    "year",
    "citations",
    "status",
    "pre_indexed_publication",
]
TOTAL_FIELDS = [
    "article_id",
    "role",
    "work_ids",
    "indexed_publication_year",
    "panel_first_year",
    "api_count",
    "sum_counts",
    "before_publication",
    "status",
    "detail",
    "source_url",
    "source_path",
    "source_sha256",
    "retrieved_at",
]


def grouped_counts(payload):
    counts = {}
    for group in payload["group_by"]:
        key, value = str(group["key"]), group["count"]
        if not key.isdigit() or not 1500 <= int(key) <= LAST_YEAR:
            raise ValueError("invalid_or_unknown_citing_year")
        if type(value) is not int or value < 0 or int(key) in counts:
            raise ValueError("invalid_or_duplicate_year_count")
        counts[int(key)] = value
    total = payload["meta"]["count"]
    if type(total) is not int or total < 0 or sum(counts.values()) != total:
        raise ValueError("grouped_counts_do_not_reconcile_to_api_total")
    return counts, total


def roster():
    original_ids = {r["article_id"] for r in sources.read("assessment_inventory.csv")}
    aliases = collections.defaultdict(set)
    for row in sources.read("control_aliases.csv"):
        aliases[row["article_id"]].add(row["alias_openalex_id"])
    doi_aliases = collections.defaultdict(set)
    for row in sources.read("verified_metadata.csv"):
        if row["doi"] and row["openalex_id"]:
            doi_aliases[row["doi"]].add(row["openalex_id"])
    controls = {r["article_id"]: r for r in sources.read("control_articles.csv")}
    extra = common.ROOT / "data/trajectories/comparison_articles.csv"
    if extra.exists():
        controls.update({r["article_id"]: r for r in common.read_csv(extra)})
        for row in common.read_csv(extra.with_name("comparison_members.csv")):
            aliases[row["article_id"]].add(row["openalex_id"])
    decisions = extra.with_name("comparison_metadata_decisions.csv")
    if decisions.exists():
        for row in common.read_csv(decisions):
            aliases[row["article_id"]].add(row["publisher_openalex_id"])
    records = []
    for role, rows in [
        ("original", sources.read("articles.csv")),
        ("control", controls.values()),
    ]:
        for row in rows:
            if role == "original" and row["article_id"] not in original_ids:
                continue
            ids = {row["openalex_id"]} | aliases[row["article_id"]]
            ids |= doi_aliases.get(row["doi"], set())
            ids.discard("")
            records.append(row | {"role": role, "work_ids": "|".join(sorted(ids))})
    common.unique(records, ["article_id"])
    return records


def query(row):
    return common.api_url(
        "works",
        filter=(
            f"cites:{row['work_ids']},type:article|review,"
            f"to_publication_date:{LAST_YEAR}-12-31"
        ),
        group_by="publication_year",
        per_page=200,
    )


def acquire(row, offline, stopped):
    result = dict.fromkeys(TOTAL_FIELDS, "")
    result.update({k: row[k] for k in ["article_id", "role", "work_ids"]})
    result["indexed_publication_year"] = row["indexed_publication_year"]
    result["status"] = "unavailable"
    annual = []
    if (
        row["identity_verified"] != "yes"
        or not row["work_ids"]
        or not result["indexed_publication_year"]
    ):
        result["detail"] = "identity_or_indexed_year_unresolved"
        return annual, result
    url = query(row)
    path = CACHE / (common.sha256(url.encode()) + ".json")
    try:
        if not path.exists() and (offline or stopped.is_set()):
            raise FileNotFoundError("response_not_cached")
        if path.exists():
            origin = json.loads(path.with_suffix(".json.source.json").read_text())
            if origin["url"] != url or origin["sha256"] != common.sha256(
                path.read_bytes()
            ):
                raise ValueError("cache_receipt_mismatch")
        payload = common.request(url, path)
        counts, total = grouped_counts(payload)
        origin = json.loads(path.with_suffix(".json.source.json").read_text())
        first = int(result["indexed_publication_year"])
        if not 1500 <= first <= LAST_YEAR + 1:
            raise ValueError("invalid_indexed_publication_year")
        start = min(first, min(counts, default=first))
        result.update(
            panel_first_year=start,
            api_count=total,
            sum_counts=sum(counts.values()),
            before_publication=sum(n for y, n in counts.items() if y < first),
            status="complete",
            source_url=url,
            source_path=str(path.relative_to(common.ROOT)),
            source_sha256=origin["sha256"],
            retrieved_at=origin["retrieved_at"],
        )
        annual = [
            dict(
                article_id=row["article_id"],
                year=y,
                citations=counts.get(y, 0),
                status="complete",
                pre_indexed_publication=y < first,
            )
            for y in range(start, LAST_YEAR + 1)
        ]
    except (OSError, ValueError, KeyError) as exc:
        if isinstance(exc, urllib.error.HTTPError) and exc.code in {402, 403, 429}:
            stopped.set()
        result["detail"] = str(exc)[:200]
    return annual, result


def validate(annual=None, totals=None):
    """Check distributed annual data against complete API count receipts."""
    if annual is None:
        annual = common.read_csv(OUT / "citations.csv")
    if totals is None:
        totals = common.read_csv(OUT / "totals.csv")
    common.unique(annual, ["article_id", "year"])
    common.unique(totals, ["article_id"])
    by_id = collections.defaultdict(list)
    known = {r["article_id"] for r in totals}
    for row in annual:
        if row["article_id"] not in known:
            raise ValueError("annual_history_without_receipt")
        by_id[row["article_id"]].append(row)
    for receipt in totals:
        rows = by_id[receipt["article_id"]]
        if receipt["status"] != "complete":
            if rows:
                raise ValueError("unavailable_history_has_observations")
            continue
        expected = set(range(int(receipt["panel_first_year"]), LAST_YEAR + 1))
        if {int(r["year"]) for r in rows} != expected:
            raise ValueError("annual_history_has_missing_or_extra_years")
        if any(int(r["citations"]) < 0 or r["status"] != "complete" for r in rows):
            raise ValueError("invalid_annual_observation")
        total = sum(int(r["citations"]) for r in rows)
        if total != int(receipt["api_count"]) or total != int(receipt["sum_counts"]):
            raise ValueError("annual_history_does_not_reconcile")
        first = int(receipt["indexed_publication_year"])
        before = sum(int(r["citations"]) for r in rows if int(r["year"]) < first)
        if before != int(receipt["before_publication"]):
            raise ValueError("pre_indexed_counts_do_not_reconcile")
    print(f"Validated {len(totals)} receipts and {len(annual)} annual observations")


def build(offline=True, workers=4, only=None):
    rows = roster()
    if only:
        rows = [r for r in rows if r["role"] == only]
    stopped = threading.Event()
    annual, totals = [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(acquire, row, offline, stopped) for row in rows]
        for done, future in enumerate(concurrent.futures.as_completed(futures), 1):
            series, total = future.result()
            annual.extend(series)
            totals.append(total)
            if not offline and done % 100 == 0:
                print(f"{done}/{len(rows)} histories checked", flush=True)
    if only and (OUT / "totals.csv").exists():
        prior = common.read_csv(OUT / "totals.csv")
        keep = {r["article_id"] for r in prior if r["role"] != only}
        totals.extend(r for r in prior if r["article_id"] in keep)
        annual.extend(
            r for r in common.read_csv(OUT / "citations.csv") if r["article_id"] in keep
        )
    annual.sort(key=lambda r: (r["article_id"], int(r["year"])))
    totals.sort(key=lambda r: r["article_id"])
    common.unique(annual, ["article_id", "year"])
    common.unique(totals, ["article_id"])
    common.write_csv(OUT / "citations.csv", annual, CITATION_FIELDS)
    common.write_csv(OUT / "totals.csv", totals, TOTAL_FIELDS)
    edges = {
        (r["article_id"], int(r["year"])): int(r["citations"])
        for r in sources.read("citations.csv")
        if r["status"] == "complete"
    }
    comparison = [
        dict(
            article_id=r["article_id"],
            year=r["year"],
            grouped=int(r["citations"]),
            deduplicated_edges=edges[r["article_id"], int(r["year"])],
            difference=int(r["citations"]) - edges[r["article_id"], int(r["year"])],
        )
        for r in annual
        if (r["article_id"], int(r["year"])) in edges
    ]
    common.write_csv(
        OUT / "edge_comparison.csv",
        comparison,
        ["article_id", "year", "grouped", "deduplicated_edges", "difference"],
    )
    print(
        json.dumps(
            dict(
                histories=dict(
                    collections.Counter(r["role"] + "/" + r["status"] for r in totals)
                ),
                paper_years=len(annual),
                comparison_years=len(comparison),
                agreeing_years=sum(r["difference"] == 0 for r in comparison),
                max_absolute_difference=max(
                    (abs(r["difference"]) for r in comparison), default=None
                ),
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--only", choices=["original", "control"])
    args = parser.parse_args()
    if args.workers < 1 or args.workers > 8:
        parser.error("workers must be between 1 and 8")
    if args.validate:
        validate()
    else:
        build(not args.fetch, args.workers, args.only)
