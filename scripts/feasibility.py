"""Audit existing coverage and prepare a probability sample for claim-use review."""

from __future__ import annotations

import collections
import hashlib
import json

import common

DATA = common.ROOT / "data/i4r"
OUT = common.ROOT / "data/feasibility"
CUTOFF = 2025
SEED = "i4r-response-2026-11-04"
PER_CLAIM = 5


def indexed(rows, key):
    common.unique(rows, [key])
    return {row[key]: row for row in rows}


def validate_event_coverage(events, claims):
    """Missing or extra event records must not silently change the claim roster."""
    common.unique(events, ["assessment_id"])
    if {row["assessment_id"] for row in events} != set(claims):
        raise ValueError("Claim/event coverage mismatch")


def claim_status(event, article, cutoff=CUTOFF):
    """Eligibility for descriptive post-disclosure review, not a causal sample."""
    reasons = []
    if event["error_verified"] != "yes" or event["material"] != "yes":
        reasons.append("material_error_not_verified")
    if event["publicity_verified"] != "yes" or not event["year"]:
        reasons.append("public_disclosure_unverified")
    if event["already_retracted"] != "no":
        reasons.append("retraction_status_not_eligible")
    if article.get("identity_verified") != "yes":
        reasons.append("original_identity_unverified")
    if event["year"] and int(event["year"]) >= cutoff:
        reasons.append("no_complete_post_disclosure_year")
    return ";".join(reasons) or "candidate_for_context_review"


def sample_edges(edges, assessment_id, event_year, complete, limit=PER_CLAIM):
    """Sample unique citing works in the first full post year; missing is not zero."""
    if not complete:
        return [], None
    common.unique(edges, ["citing_work_id"])
    candidates = [
        row
        for row in edges
        if row["publication_year"] == str(event_year + 1)
        and row["type"] in {"article", "review"}
    ]
    candidates.sort(
        key=lambda row: hashlib.sha256(
            f"{SEED}|{assessment_id}|{row['citing_work_id']}".encode()
        ).hexdigest()
    )
    return candidates[:limit], len(candidates)


def build():
    def read(name):
        return common.read_csv(DATA / name)

    sources = read("sources.csv")
    units = read("assessment_inventory.csv")
    articles = indexed(read("articles.csv"), "article_id")
    claims = indexed(read("assessments.csv"), "assessment_id")
    events = read("events.csv")
    common.unique(units, ["unit_id"])
    common.unique(events, ["event_id"])
    common.unique(events, ["assessment_id"])
    validate_event_coverage(events, claims)
    source_ids = {row["source_id"] for row in sources}
    for unit in units:
        if unit["article_id"] not in articles:
            raise ValueError("Assessment refers to an unknown original")
    for event in events:
        claim = claims[event["assessment_id"]]
        if (
            event["article_id"] != claim["article_id"]
            or event["source_id"] != claim["source_id"]
            or event["source_id"] not in source_ids
        ):
            raise ValueError("Event/claim/source identity conflict")
    retrieval = indexed(read("citation_retrieval.csv"), "article_id")
    edges = collections.defaultdict(list)
    for edge in read("citation_edges.csv"):
        edges[edge["article_id"]].append(edge)

    windows, queue = [], []
    for event in sorted(events, key=lambda row: row["assessment_id"]):
        aid = event["article_id"]
        article = articles[aid]
        claim = claims[event["assessment_id"]]
        status = claim_status(event, article)
        history = retrieval.get(aid, {}).get("status", "not_collected")
        selected, population = [], None
        if status == "candidate_for_context_review":
            selected, population = sample_edges(
                edges[aid],
                claim["assessment_id"],
                int(event["year"]),
                history == "complete",
            )
        windows.append(
            dict(
                assessment_id=claim["assessment_id"],
                article_id=aid,
                source_id=claim["source_id"],
                title=article["title"],
                doi=article["doi"],
                category=claim["category"],
                dispute_status=claim["dispute_status"],
                affected_claim=claim["affected_claim"],
                disclosure_date=event["date"],
                date_precision=event["date_precision"],
                disclosure_year=event["year"],
                complete_post_years=(
                    max(0, CUTOFF - int(event["year"])) if event["year"] else ""
                ),
                review_eligibility=status,
                citation_history_status=history,
                first_post_year_citing_works=(
                    population if population is not None else ""
                ),
            )
        )
        for rank, edge in enumerate(selected, 1):
            queue.append(
                dict(
                    assessment_id=claim["assessment_id"],
                    article_id=aid,
                    original_doi=article["doi"],
                    affected_claim=claim["affected_claim"],
                    source_id=claim["source_id"],
                    assessment_evidence_locator=claim["evidence_locator"],
                    citing_work_id=edge["citing_work_id"],
                    citing_doi=edge["citing_doi"],
                    publication_year=edge["publication_year"],
                    population_citing_works=population,
                    sample_size=len(selected),
                    inclusion_probability=len(selected) / population,
                    sample_rank=rank,
                    claim_packet_temporal_review="pending",
                    publication_date=edge["publication_date"],
                    fulltext_status="not_checked",
                    coding_status="pending",
                )
            )
    common.unique(queue, ["assessment_id", "citing_work_id"])
    OUT.mkdir(exist_ok=True, parents=True)
    common.write_csv(OUT / "claim_bundle_windows.csv", windows, list(windows[0]))
    fields = [
        "assessment_id",
        "article_id",
        "original_doi",
        "affected_claim",
        "source_id",
        "assessment_evidence_locator",
        "citing_work_id",
        "citing_doi",
        "publication_year",
        "population_citing_works",
        "sample_size",
        "inclusion_probability",
        "sample_rank",
        "publication_date",
        "claim_packet_temporal_review",
        "fulltext_status",
        "coding_status",
    ]
    common.write_csv(OUT / "context_review_queue.csv", queue, fields)
    native = collections.Counter(
        (row["disposition"], row["assessment_resolved"]) for row in units
    )
    common.write_csv(
        OUT / "native_dispositions.csv",
        [
            dict(disposition=k[0], assessment_resolved=k[1], assessment_units=v)
            for k, v in sorted(native.items())
        ],
        ["disposition", "assessment_resolved", "assessment_units"],
    )
    eligible = [
        r for r in windows if r["review_eligibility"] == "candidate_for_context_review"
    ]
    summary = {
        "catalog_cutoff": "2026-10-05",
        "citation_cutoff_year": CUTOFF,
        "catalog_listings": len(sources),
        "assessment_units": len(units),
        "distinct_assessed_originals": len({r["article_id"] for r in units}),
        "resolved_assessment_units": sum(
            r["assessment_resolved"] == "yes" for r in units
        ),
        "unresolved_assessment_units": sum(
            r["assessment_resolved"] != "yes" for r in units
        ),
        "curated_claim_bundles": len(claims),
        "context_candidate_bundles": len(eligible),
        "context_candidate_originals": len({r["article_id"] for r in eligible}),
        "candidate_bundles_complete_history": sum(
            r["citation_history_status"] == "complete" for r in eligible
        ),
        "sampled_bundle_citing_work_pairs": len(queue),
        "sampled_unique_citing_works": len({r["citing_work_id"] for r in queue}),
        "bundles_in_context_queue": len({r["assessment_id"] for r in queue}),
        "bundle_eligibility_reasons": dict(
            collections.Counter(r["review_eligibility"] for r in windows)
        ),
        "context_ratings_completed": 0,
        "seed": SEED,
        "decision": "narrow_and_test",
    }
    (OUT / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    report = f"""# I4R response: feasibility audit

Decision: **narrow and test**. Citation persistence alone is not a new contribution.
The candidate extension measures whether subsequent authors use the specific
challenged claim, qualify it, or use an unaffected part of the original article.
This requires new full-text assessment; no such result is reported here.

| Stage | Count |
|---|---:|
| Frozen catalog listings | {len(sources)} |
| Enumerated assessment units | {len(units)} |
| Distinct originals in those assessments | {summary['distinct_assessed_originals']} |
| Resolved assessment units | {summary['resolved_assessment_units']} |
| Unresolved assessment units | {summary['unresolved_assessment_units']} |
| Curated claim-bundle records | {len(claims)} |
| Bundles passing initial identity/date/materiality screens | {len(eligible)} |
| Candidate originals | {summary['context_candidate_originals']} |
| Complete cached histories | {summary['candidate_bundles_complete_history']} |
| Bundles represented in the review queue | {summary['bundles_in_context_queue']} |
| Sampled bundle–citing-work pairs | {len(queue)} |
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
"""
    (common.ROOT / "docs/feasibility.md").write_text(report)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    build()
