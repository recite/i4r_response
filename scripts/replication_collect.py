"""Collect seeded journal/year donor pools and comparable annual citation counts."""

from __future__ import annotations

import argparse
import collections
import concurrent.futures
import json
import threading
import urllib.request

import collect_comparison_pools as pools
import collect_grouped_citations as grouped
import common
import i4r_registry as registry
import replication_events as events
import replication_metadata as metadata
import replication_sources as source

OUT = common.ROOT / "data/expansion"
CACHE = common.ROOT / "private-data/expansion"


def account():
    request = urllib.request.Request(
        "https://api.openalex.org/rate-limit",
        headers={"Authorization": "Bearer " + common.openalex_api_key()},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)["rate_limit"]


def collect_pools(fetch=False):
    targets = [
        r
        for r in common.read_csv(OUT / "events.csv")
        if r["status"] == "candidate_for_matching"
    ]
    keys = {(r["journal_id"], r["indexed_year"], r["type"]) for r in targets}
    pools.CACHE = CACHE / "comparison_pools"
    samples, members, works = [], [], {}

    def acquire(key):
        journal, year, kind = key
        return pools.sample_pool(
            dict(journal_id=journal, indexed_publication_year=year, type=kind),
            not fetch,
            fetcher=lambda url, path: metadata.cached(
                url, "comparison_pools", fetch, CACHE
            )[0],
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(acquire, sorted(keys)))
    for n, (row, result) in enumerate(results, 1):
        samples.append(row)
        for work in result:
            doi = source.doi(work.get("doi") or "")
            aid = (
                events.paper_id(doi) if doi else "work_" + work["id"].rsplit("/", 1)[-1]
            )
            works[aid] = work
            members.append(
                dict(pool_id=row["event_id"], article_id=aid, openalex_id=work["id"])
            )
        if n % 50 == 0:
            print(f"Pools {n}/{len(keys)}", flush=True)
    candidates = []
    for aid, work in sorted(works.items()):
        r = registry.article_from_work(work, aid)
        r["title"] = r["title"] or ""
        if type(work.get("is_retracted")) is not bool:
            r["retracted"] = "unknown"
        candidates.append(r)
    dates = metadata.crossref_many(
        sorted({r["doi"] for r in candidates if source.doi(r["doi"])}), fetch
    )
    date_by = {r["doi"]: r for r in dates}
    known = common.read_csv(OUT / "flora_candidates.csv")
    excluded = {source.doi(r[k]) for r in known for k in ["doi_o", "doi_r"]} - {""}
    excluded |= {
        r["doi"]
        for r in common.read_csv(common.ROOT / "data/i4r/articles.csv")
        if r["doi"]
    }
    manual_path = OUT / "comparison_manual_exclusions.csv"
    manual = (
        {r["article_id"] for r in common.read_csv(manual_path)}
        if manual_path.exists()
        else set()
    )
    nonresearch = []
    for r in candidates:
        d = date_by.get(r["doi"], {})
        reasons = []
        if r["article_id"] in manual:
            reasons.append("reviewed_nonresearch")
        if r["doi"] in excluded:
            reasons.append("known_assessed_original_or_assessment_report")
        if r["retracted"] != "no":
            reasons.append("current_retraction_flag")
        if not d.get("publisher_date") or d.get("publisher_type") != "journal-article":
            reasons.append("publisher_journal_date_unavailable")
        if not events.title_matches(r["title"], d.get("publisher_title", "")):
            reasons.append("publisher_title_review_required")
        title = registry.title_key(r["title"])
        if any(
            title.startswith(x)
            for x in [
                "frontmatter",
                "backmatter",
                "editorial",
                "erratum",
                "corrigendum",
                "retraction",
                "correctionto",
                "acknowledg",
                "listofreviewers",
                "recentreferees",
                "indexof",
                "annualreport",
            ]
        ):
            reasons.append("nonresearch_title")
        if reasons:
            nonresearch.append(
                dict(
                    article_id=r["article_id"],
                    reasons=";".join(reasons),
                    title=r["title"],
                )
            )
        r.update(
            publication_date=d.get("publisher_date", ""),
            publication_year=d.get("publisher_date", "")[:4],
            publication_date_source=d.get("crossref_record_url", ""),
        )
    common.unique(members, ["pool_id", "article_id", "openalex_id"])
    common.write_csv(OUT / "comparison_pools.csv", samples, pools.POOL_FIELDS)
    common.write_csv(
        OUT / "comparison_members.csv",
        members,
        ["pool_id", "article_id", "openalex_id"],
    )
    common.write_csv(
        OUT / "comparison_articles.csv", candidates, registry.ARTICLE_FIELDS
    )
    common.write_csv(OUT / "comparison_metadata.csv", dates, list(dates[0]))
    metadata.source_receipts()
    common.write_csv(
        OUT / "comparison_exclusions.csv",
        nonresearch,
        ["article_id", "reasons", "title"],
    )
    print(
        json.dumps(
            dict(
                pools=len(samples),
                pool_status=dict(collections.Counter(r["status"] for r in samples)),
                candidates=len(candidates),
                excluded=len(nonresearch),
            ),
            indent=2,
        )
    )


def history_roster():
    originals = [
        r
        for r in common.read_csv(OUT / "events.csv")
        if r["status"] == "candidate_for_matching"
    ]
    rows = [
        dict(
            article_id=r["article_id"],
            role="original",
            work_ids=r["openalex_id"],
            indexed_publication_year=r["indexed_year"],
            identity_verified="yes",
        )
        for r in originals
    ]
    excluded = {
        r["article_id"] for r in common.read_csv(OUT / "comparison_exclusions.csv")
    }
    aliases = collections.defaultdict(set)
    for r in common.read_csv(OUT / "comparison_members.csv"):
        aliases[r["article_id"]].add(r["openalex_id"])
    order = {}
    for member in common.read_csv(OUT / "comparison_members.csv"):
        aid = member["article_id"]
        order[aid] = min(order.get(aid, member["pool_id"]), member["pool_id"])
    controls = common.read_csv(OUT / "comparison_articles.csv")
    for r in sorted(controls, key=lambda r: (order[r["article_id"]], r["article_id"])):
        if r["article_id"] not in excluded:
            rows.append(
                dict(
                    article_id=r["article_id"],
                    role="control",
                    work_ids="|".join(sorted(aliases[r["article_id"]])),
                    indexed_publication_year=r["indexed_publication_year"],
                    identity_verified=r["identity_verified"],
                )
            )
    common.unique(rows, ["article_id"])
    return rows


def collect_histories(fetch=False, max_paid_usd=0):
    rows = history_roster()
    grouped.CACHE = CACHE / "grouped_citations"
    stopped = threading.Event()
    annual, totals = [], []
    initial = account() if fetch else {}
    initial_balance = initial.get("prepaid_remaining_usd", 0)
    cost_path = OUT / "collection_cost.json"
    previous = json.loads(cost_path.read_text()) if cost_path.exists() else {}
    prior_paid = previous.get("provider_reported_prepaid_debit", 0)
    for start in range(0, len(rows), 100):
        stop = start + 100
        batch = rows[start:stop]
        if fetch and not stopped.is_set():
            current = account()
            paid = initial_balance - current["prepaid_remaining_usd"]
            missing = sum(
                not (
                    grouped.CACHE / (common.sha256(grouped.query(r).encode()) + ".json")
                ).exists()
                for r in batch
            )
            reserve = missing * 4 * 0.0001
            if (
                reserve
                > current["daily_remaining_usd"] + max_paid_usd - paid - prior_paid
            ):
                stopped.set()
                print(
                    "Budget stop: remaining requests recorded as unavailable",
                    flush=True,
                )
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            for series, total in executor.map(
                lambda r: grouped.acquire(r, not fetch, stopped), batch
            ):
                if stopped.is_set() and total["detail"] == "response_not_cached":
                    total["detail"] = "budget_stop"
                annual.extend(series)
                totals.append(total)
        print(f"Histories {min(start + 100, len(rows))}/{len(rows)}", flush=True)
    annual.sort(key=lambda r: (r["article_id"], int(r["year"])))
    totals.sort(key=lambda r: r["article_id"])
    grouped.validate(annual, totals)
    common.write_csv(OUT / "citations.csv", annual, grouped.CITATION_FIELDS)
    common.write_csv(OUT / "citation_totals.csv", totals, grouped.TOTAL_FIELDS)
    if fetch:
        final = account()
        (OUT / "collection_cost.json").write_text(
            json.dumps(
                dict(
                    allowed_paid_usd=max_paid_usd,
                    provider_reported_prepaid_debit=round(
                        prior_paid + initial_balance - final["prepaid_remaining_usd"], 6
                    ),
                    daily_usage_increase=round(
                        final["daily_used_usd"] - initial["daily_used_usd"], 6
                    ),
                    qualification=(
                        "Account-level changes during this run; "
                        "concurrent account activity may contribute."
                    ),
                ),
                indent=2,
            )
            + "\n"
        )
    print(
        json.dumps(
            dict(collections.Counter(r["role"] + "/" + r["status"] for r in totals)),
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["pools", "histories"])
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--max-paid-usd", type=float, default=0)
    args = parser.parse_args()
    if args.stage == "pools":
        collect_pools(args.fetch)
    else:
        collect_histories(args.fetch, args.max_paid_usd)
