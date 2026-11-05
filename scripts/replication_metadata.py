"""Verify replication-pair DOI metadata with Crossref and OpenAlex snapshots."""

from __future__ import annotations

import argparse
import collections
import json
import urllib.parse

import common
import replication_sources as source

OUT = common.ROOT / "data/expansion"
CACHE = common.ROOT / "private-data/expansion/metadata"
SELECT = (
    "id,doi,title,publication_year,publication_date,type,is_retracted,primary_location"
)


def cached(url, folder, fetch=False, cache_root=CACHE):
    path = cache_root / folder / (common.sha256(url.encode()) + ".json")
    if path.exists():
        receipt = json.loads(path.with_suffix(".json.source.json").read_text())
        if receipt["url"] != url or receipt["sha256"] != common.sha256(
            path.read_bytes()
        ):
            raise ValueError("metadata_receipt_mismatch")
    elif not fetch:
        raise FileNotFoundError("metadata_not_cached")
    payload = common.request(url, path)
    receipt = json.loads(path.with_suffix(".json.source.json").read_text())
    return payload, receipt


def dated(work):
    dates = []
    for field in ["published-online", "published-print", "published"]:
        parts = work.get(field, {}).get("date-parts", [[]])[0]
        if parts and 1500 <= parts[0] <= 2026:
            dates.append(
                "-".join(str(x).zfill(4 if i == 0 else 2) for i, x in enumerate(parts))
            )
    return min(dates, default="")


def crossref(doi, fetch=False, snapshot=None):
    row = dict(
        doi=doi,
        crossref_status="unavailable",
        publisher_date="",
        publisher_type="",
        publisher_title="",
        publisher_journal="",
        crossref_record_url="",
        crossref_sha256="",
        crossref_retrieved_at="",
        detail="",
    )
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="")
    try:
        payload, receipt = snapshot if snapshot else cached(url, "crossref", fetch)
        work = payload["message"]
        if common.normalize_doi(work["DOI"]) != doi:
            raise ValueError("crossref_doi_mismatch")
        row.update(
            crossref_status="complete",
            publisher_date=dated(work),
            publisher_type=work.get("type", ""),
            publisher_title="; ".join(work.get("title", [])),
            publisher_journal="; ".join(work.get("container-title", [])),
            crossref_record_url=url,
            crossref_sha256=receipt["sha256"],
            crossref_retrieved_at=receipt["retrieved_at"],
        )
    except (OSError, ValueError, KeyError) as exc:
        row["detail"] = str(exc)[:180]
    return row


def cohort_dois():
    rows = common.read_csv(OUT / "flora_candidates.csv")
    return sorted(
        {
            source.doi(r[k])
            for r in rows
            if r["type"] == "replication"
            for k in ["doi_o", "doi_r"]
        }
        - {""}
    )


def crossref_many(dois, fetch=False):
    records = []
    ordinary = [d for d in dois if "," not in d]
    for start in range(0, len(ordinary), 50):
        stop = start + 50
        batch = ordinary[start:stop]
        url = "https://api.crossref.org/works?" + urllib.parse.urlencode(
            dict(
                filter=",".join("doi:" + d for d in batch),
                rows=100,
                select=(
                    "DOI,title,type,published,published-online,"
                    "published-print,container-title"
                ),
            )
        )
        try:
            payload, receipt = cached(url, "crossref_batches", fetch)
            items = payload["message"]["items"]
            if len(items) != payload["message"]["total-results"]:
                raise ValueError("truncated_crossref_batch")
            found = {common.normalize_doi(w["DOI"]): w for w in items}
            if not set(found) <= set(batch) or len(found) != len(items):
                raise ValueError("unexpected_or_duplicate_crossref_doi")
            for doi in batch:
                records.append(
                    crossref(doi, False, ({"message": found[doi]}, receipt))
                    if doi in found
                    else crossref(doi, False)
                )
        except (OSError, ValueError, KeyError):
            records.extend(crossref(doi, False) for doi in batch)
        if start % 500 == 0:
            print(f"Crossref {min(start + 50, len(ordinary))}/{len(dois)}", flush=True)
    records.extend(crossref(doi, fetch) for doi in dois if "," in doi)
    return records


def source_receipts():
    rows = []
    for path in sorted(CACHE.rglob("*.source.json")):
        receipt = json.loads(path.read_text())
        rows.append(
            dict(
                source_sha256=receipt["sha256"],
                source_url=receipt["url"],
                retrieved_at=receipt["retrieved_at"],
                bytes=receipt["bytes"],
                source_path=str(path.relative_to(common.ROOT)).removesuffix(
                    ".source.json"
                ),
            )
        )
    common.write_csv(OUT / "metadata_sources.csv", rows, list(rows[0]))


def openalex_batch(payload, requested):
    items = payload["results"]
    if payload["meta"]["count"] != len(items):
        raise ValueError("truncated_openalex_batch")
    accepted = {}
    for work in items:
        doi = common.normalize_doi(work.get("doi") or "")
        if doi in requested:
            if doi in accepted:
                raise ValueError("multiple_openalex_records_for_doi")
            accepted[doi] = work
    return accepted


def build(fetch=False):
    dois = cohort_dois()
    records = crossref_many(dois, fetch)
    records.sort(key=lambda r: r["doi"])
    works, retrieval = {}, []
    for start in range(0, len(dois), 50):
        stop = start + 50
        batch = dois[start:stop]
        values = [f'"{d}"' if "," in d else d for d in batch]
        url = common.api_url(
            "works", filter="doi:" + "|".join(values), per_page=100, select=SELECT
        )
        try:
            payload, receipt = cached(url, "openalex", fetch)
            accepted = openalex_batch(payload, batch)
            works.update({d: w | {"receipt": receipt} for d, w in accepted.items()})
            retrieval.append(
                dict(
                    batch=start // 50,
                    status="complete",
                    requested=len(batch),
                    returned=len(payload["results"]),
                    source_url=url,
                    detail="",
                )
            )
        except (OSError, ValueError, KeyError) as exc:
            retrieval.append(
                dict(
                    batch=start // 50,
                    status="unavailable",
                    requested=len(batch),
                    returned="",
                    source_url=url,
                    detail=str(exc)[:180],
                )
            )
        if start % 500 == 0:
            print(f"OpenAlex {min(start + 50, len(dois))}/{len(dois)}", flush=True)
    common.write_csv(OUT / "metadata_retrieval.csv", retrieval, list(retrieval[0]))
    for row in records:
        w = works.get(row["doi"], {})
        journal = (w.get("primary_location") or {}).get("source") or {}
        receipt = w.get("receipt", {})
        row.update(
            openalex_id=w.get("id", ""),
            indexed_year=w.get("publication_year", ""),
            indexed_date=w.get("publication_date", ""),
            openalex_type=w.get("type", ""),
            openalex_title=w.get("title", ""),
            journal_id=journal.get("id", ""),
            journal=journal.get("display_name", ""),
            retracted=w.get("is_retracted", ""),
            openalex_record_url=(
                ("https://api.openalex.org/works/" + w["id"].rsplit("/", 1)[-1])
                if w
                else ""
            ),
            openalex_sha256=receipt.get("sha256", ""),
            openalex_retrieved_at=receipt.get("retrieved_at", ""),
        )
    common.write_csv(OUT / "metadata.csv", records, list(records[0]))
    source_receipts()
    print(
        json.dumps(
            dict(
                dois=len(dois),
                crossref=dict(
                    collections.Counter(r["crossref_status"] for r in records)
                ),
                openalex=len(works),
                publisher_dates=sum(bool(r["publisher_date"]) for r in records),
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true")
    args = parser.parse_args()
    build(args.fetch)
