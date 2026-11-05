"""Collect seeded journal/year comparison samples, then verify publisher dates.

Adapted from propagation_of_error scripts/openalex/03_pools.py at
aba3475109fec6099b91801f4ac9d7149639d78c: random candidate samples avoid
OpenAlex's default citation-sorted first page. A complete sample is not a census.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json

import common
import i4r_registry as registry
import i4r_sources as sources
import trajectory_basics as study

OUT = study.OUT
CACHE = sources.CACHE / "comparison_pools"
SEED = 20261028
SAMPLE = 20
SELECT = (
    "id,doi,title,publication_year,publication_date,type,is_retracted,primary_location"
)
POOL_FIELDS = [
    "event_id",
    "journal_id",
    "year",
    "type",
    "status",
    "query_filter",
    "pool_count",
    "sample_size",
    "seed",
    "complete_pool",
    "detail",
]
MEMBER_FIELDS = ["pool_id", "article_id", "openalex_id", "doi"]


def sample_pool(article, offline):
    year = article["indexed_publication_year"]
    query = (
        f"primary_location.source.id:{article['journal_id']},"
        f"publication_year:{year},type:{article['type']}"
    )
    pid = "sample_" + hashlib.sha256(query.encode()).hexdigest()[:16]
    row = dict.fromkeys(POOL_FIELDS, "") | dict(
        event_id=pid,
        journal_id=article["journal_id"],
        year=year,
        type=article["type"],
        status="unavailable",
        query_filter=query,
        seed=SEED,
    )
    try:
        payloads = []
        for params in [
            dict(per_page=1, select="id"),
            dict(sample=SAMPLE, seed=SEED, per_page=SAMPLE, select=SELECT),
        ]:
            url = common.api_url("works", filter=query, **params)
            path = CACHE / (common.sha256(url.encode()) + ".json")
            if offline and not path.exists():
                raise FileNotFoundError("response_not_cached")
            payloads.append(sources.fetch(url, path))
        count = payloads[0]["meta"]["count"]
        works = payloads[1]["results"]
        if len(works) != min(SAMPLE, count) or len({w["id"] for w in works}) != len(
            works
        ):
            raise ValueError("incomplete_or_duplicate_candidate_sample")
        for work in works:
            if (
                str(work["publication_year"]) != year
                or work["type"] != article["type"]
                or work["primary_location"]["source"]["id"] != article["journal_id"]
            ):
                raise ValueError("candidate_outside_requested_journal_year")
        row.update(
            status="complete",
            pool_count=count,
            sample_size=len(works),
            complete_pool=count <= SAMPLE,
        )
        return row, works
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        row["detail"] = str(exc)[:180]
        return row, []


def publisher_metadata(row, offline, decisions=None):
    decision = (decisions or {}).get(row["article_id"])
    if decision:
        if decision["sampled_doi"] != row["doi"]:
            raise ValueError("Publisher decision does not match sampled identity")
        path = common.ROOT / decision["source_path"]
        if common.sha256(path.read_bytes()) != decision["source_sha256"]:
            raise ValueError("Publisher metadata receipt mismatch")
        work = json.loads(path.read_text())["message"]
        if common.normalize_doi(work["DOI"]) != decision["publisher_doi"]:
            raise ValueError("Publisher decision DOI mismatch")
        resolved = registry.publisher_date(
            row | {"doi": decision["publisher_doi"]}, work
        )
        for field in [
            "publication_date",
            "publication_year",
            "publication_date_source",
        ]:
            row[field] = resolved[field]
        return row
    if row["publication_date_source"] or not row["doi"]:
        return row
    path = sources.CACHE / "crossref" / (row["article_id"] + ".json")
    if not offline:
        registry.crossref_record(row)
    if path.exists():
        work = json.loads(path.read_text())["message"]
        matched = registry.crossref_title_match(row["title"], [work], known_doi=True)
        if matched and common.normalize_doi(work["DOI"]) == row["doi"]:
            registry.publisher_date(row, work)
    return row


def build(offline=True):
    articles = study.index(sources.read("articles.csv"), "article_id")
    eligible = common.read_csv(OUT / "eligibility.csv")
    keys = {}
    disallowed = [
        "insufficient_full_baseline_age",
        "insufficient_complete_followup_years",
        "original_identity_unverified",
        "original_retraction_status_not_eligible",
        "original_journal_year_missing",
    ]
    full_pools = sources.read("risk_set_retrieval.csv")
    for row in eligible:
        if row["measure"] != "grouped_article_review_works" or any(
            reason in row["status"] for reason in disallowed
        ):
            continue
        article = articles[row["article_id"]]
        if any(study.pool_covers(pool, article) for pool in full_pools):
            continue
        keys[
            article["journal_id"], article["indexed_publication_year"], article["type"]
        ] = article
    known = sources.read("control_articles.csv")
    by_doi = {r["doi"]: r for r in known if r["doi"]}
    by_work = {r["openalex_id"]: r for r in known}
    controls, members, pools = {}, [], []
    for i, article in enumerate([keys[k] for k in sorted(keys)], 1):
        pool, works = sample_pool(article, offline)
        pools.append(pool)
        for work in works:
            doi = common.normalize_doi(work.get("doi") or "")
            row = by_doi.get(doi) or by_work.get(work["id"])
            if row is None:
                aid = (
                    "control_"
                    + hashlib.sha256((doi or work["id"]).encode()).hexdigest()[:14]
                )
                row = registry.add_retraction(registry.article_from_work(work, aid))
            else:
                row = dict(row)
            controls[row["article_id"]] = row
            members.append(
                dict(
                    pool_id=pool["event_id"],
                    article_id=row["article_id"],
                    openalex_id=work["id"],
                    doi=doi,
                )
            )
        if not offline and i % 10 == 0:
            print(f"{i}/{len(keys)} journal/year pools", flush=True)
    # Canonical DOI aliases are not independent candidate papers.
    members = list(
        {(r["pool_id"], r["article_id"], r["openalex_id"]): r for r in members}.values()
    )
    decision_path = OUT / "comparison_metadata_decisions.csv"
    decisions = (
        {r["article_id"]: r for r in common.read_csv(decision_path)}
        if decision_path.exists()
        else {}
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        records = list(
            executor.map(
                lambda r: publisher_metadata(r, offline, decisions), controls.values()
            )
        )
    records.sort(key=lambda r: r["article_id"])
    members.sort(key=lambda r: (r["pool_id"], r["article_id"]))
    common.unique(records, ["article_id"])
    common.unique(members, ["pool_id", "article_id", "openalex_id"])
    common.write_csv(OUT / "comparison_pools.csv", pools, POOL_FIELDS)
    common.write_csv(OUT / "comparison_articles.csv", records, registry.ARTICLE_FIELDS)
    common.write_csv(OUT / "comparison_members.csv", members, MEMBER_FIELDS)
    print(
        json.dumps(
            dict(
                pools=len(pools),
                complete_samples=sum(p["status"] == "complete" for p in pools),
                candidate_articles=len(records),
                publisher_dates=sum(
                    bool(r["publication_date_source"]) for r in records
                ),
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true")
    args = parser.parse_args()
    build(not args.fetch)
