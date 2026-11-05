"""Construct first-recorded replication publication events before outcome filtering."""

from __future__ import annotations

import collections
import json

import common
import i4r_registry as registry
import replication_sources as source

OUT = common.ROOT / "data/expansion"


def paper_id(doi):
    return "paper_" + common.sha256(doi.encode())[:16]


def first_event(rows, metadata):
    dated = []
    uncertain = []
    for r in rows:
        d = source.doi(r["doi_r"])
        m = metadata.get(d, {})
        date = m.get("publisher_date", "")
        journal_article = (
            m.get("publisher_type") == "journal-article"
            and not d.startswith("10.2139/")
            and "ssrn" not in m.get("publisher_journal", "").lower()
        )
        if date and journal_article:
            dated.append((int(date[:4]), r))
        else:
            uncertain.append(r)
    if not dated:
        return dict(
            event_year="",
            outcome="",
            reports="",
            selected_ids="",
            chronology_status="no_verified_report_publication",
            later_assessment_year="",
        )
    year = min(y for y, _ in dated)
    initial = [r for y, r in dated if y == year]
    labels = {r["outcome"] for r in initial}
    outcome = next(iter(labels)) if len(labels) == 1 else "mixed"
    unresolved = any(
        source.year(r["year_r"]) is None or int(r["year_r"]) <= year for r in uncertain
    )
    later = [y for y, _ in dated if y > year]
    later += [
        int(r["year_r"])
        for r in uncertain
        if source.year(r["year_r"]) and int(r["year_r"]) > year
    ]
    return dict(
        event_year=year,
        outcome=outcome,
        reports=";".join(sorted({source.doi(r["doi_r"]) for r in initial})),
        selected_ids=";".join(sorted(r["id"] for r in initial)),
        chronology_status=(
            "earlier_or_same_year_unverified_report"
            if unresolved
            else "earliest_recorded_journal_report_year"
        ),
        later_assessment_year=min(later) if later else "",
    )


def title_matches(a, b):
    return bool(
        a and b and registry.identity_title_key(a) == registry.identity_title_key(b)
    )


def build():
    raw = common.read_csv(OUT / "flora_candidates.csv")
    meta = common.read_csv(OUT / "metadata.csv")
    common.unique(meta, ["doi"])
    metadata = {r["doi"]: r for r in meta}
    originals, other_assessments = collections.defaultdict(
        list
    ), collections.defaultdict(list)
    for row in raw:
        d = source.doi(row["doi_o"])
        if not d:
            continue
        (originals if row["type"] == "replication" else other_assessments)[d].append(
            row
        )
    events, links = [], []
    for doi, rows in sorted(originals.items()):
        m = metadata.get(doi, {})
        event = first_event(rows, metadata)
        year = event["event_year"]
        selected = set(event["selected_ids"].split(";"))
        row = dict(
            article_id=paper_id(doi),
            doi=doi,
            title=m.get("publisher_title") or rows[0]["title_o"],
            **event,
            original_publisher_date=m.get("publisher_date", ""),
            openalex_id=m.get("openalex_id", ""),
            indexed_year=m.get("indexed_year", ""),
            journal_id=m.get("journal_id", ""),
            journal=m.get("journal", ""),
            type=m.get("openalex_type", ""),
            retracted=m.get("retracted", ""),
            earlier_reproduction=False,
            i4r_overlap=any(r["original_in_i4r"] == "True" for r in rows),
        )
        reasons = []
        if m.get("openalex_type") != "article":
            reasons.append("original_document_type_review_required")
        if event["chronology_status"] != "earliest_recorded_journal_report_year":
            reasons.append(event["chronology_status"])
        if event["outcome"] not in {"successful", "failed"}:
            reasons.append("nonbinary_or_unresolved_outcome")
        if not m.get("openalex_id") or m.get("publisher_type") != "journal-article":
            reasons.append("original_identity_or_journal_metadata_unavailable")
        if not m.get("journal_id") or not m.get("indexed_year"):
            reasons.append("original_journal_year_missing")
        if m.get("retracted") != "False":
            reasons.append("original_current_retraction_status_not_clear")
        if not all(
            title_matches(r["title_o"], m.get("publisher_title", "")) for r in rows
        ):
            reasons.append("original_title_review_required")
        for r in rows:
            rep = metadata.get(source.doi(r["doi_r"]), {})
            is_selected = r["id"] in selected
            agrees = title_matches(r["title_r"], rep.get("publisher_title", ""))
            if is_selected and not agrees:
                reasons.append("report_title_review_required")
            if is_selected and doi == source.doi(r["doi_r"]):
                reasons.append("original_equals_replication")
            links.append(
                dict(
                    article_id=row["article_id"],
                    source_pair_id=r["id"],
                    replication_doi=r["doi_r"],
                    source_outcome=r["outcome"],
                    source_year=r["year_r"],
                    publisher_date=rep.get("publisher_date", ""),
                    publisher_type=rep.get("publisher_type", ""),
                    selected=is_selected,
                    title_matches=agrees,
                    source_collection=r["source"],
                )
            )
        if year:
            row["earlier_reproduction"] = any(
                source.year(r["year_r"]) is None or int(r["year_r"]) <= year
                for r in other_assessments[doi]
            )
            date = m.get("publisher_date", "")
            if not date or int(date[:4]) >= year - 2:
                reasons.append("insufficient_full_baseline_age")
            if year + 1 > 2025:
                reasons.append("insufficient_complete_followup_years")
        row["status"] = ";".join(sorted(set(reasons))) or "candidate_for_matching"
        events.append(row)
    common.unique(events, ["article_id"])
    common.unique(links, ["source_pair_id"])
    common.write_csv(OUT / "events.csv", events, list(events[0]))
    common.write_csv(OUT / "event_links.csv", links, list(links[0]))
    summary = dict(
        originals=len(events),
        eligible=sum(r["status"] == "candidate_for_matching" for r in events),
        eligible_outcomes=dict(
            collections.Counter(
                r["outcome"] for r in events if r["status"] == "candidate_for_matching"
            )
        ),
        exclusions=dict(
            collections.Counter(x for r in events for x in r["status"].split(";"))
        ),
    )
    (OUT / "event_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    build()
