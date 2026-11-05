"""Build the full assessment/date roster and cached citation-trajectory diagnostics."""

from __future__ import annotations

import collections
import json
import math
import statistics

import common

DATA = common.ROOT / "data/i4r"
OUT = common.ROOT / "data/trajectories"
CUTOFF = 2025
WINDOWS = {"balanced_3pre_3post": (3, 3), "short_2pre_1post": (2, 1)}


def read(name):
    return common.read_csv(DATA / (name + ".csv"))


def index(rows, field):
    common.unique(rows, [field])
    return {row[field]: row for row in rows}


def publication_before(article, year):
    date = article["publication_date"]
    return bool(article["publication_date_source"] and date and int(date[:4]) < year)


def pool_covers(pool, article):
    if pool.get("status") != "complete":
        return False
    parts = dict(x.split(":", 1) for x in pool["query_filter"].split(","))
    year = article["indexed_publication_year"]
    bounds = parts.get("publication_year", "").split("-")
    if not year or not all(x.isdigit() for x in bounds):
        return False
    return (
        parts.get("primary_location.source.id") == article["journal_id"]
        and parts.get("type") == article["type"]
        and int(bounds[0]) <= int(year) <= int(bounds[-1])
    )


def donor_retraction_eligible(article, event_year):
    if article["retracted"] != "yes":
        return True
    date = article["retraction_date"]
    return bool(date and int(date[:4]) > event_year)


def history(rows):
    common.unique(rows, ["article_id", "year"])
    result = collections.defaultdict(dict)
    for row in rows:
        if row["status"] == "complete":
            value = int(row["citations"])
            if value < 0:
                raise ValueError("Negative citation count")
            result[row["article_id"]][int(row["year"])] = value
    return result


def rank_donors(target, donors, counts, years, limit=5):
    """Rank on baseline outcomes only; a partial pool must not change selection."""
    ids = [target] + sorted(donors)
    if any(year not in counts.get(aid, {}) for aid in ids for year in years):
        raise ValueError("incomplete_baseline_histories")
    if not donors:
        return [], False
    vectors = {aid: [math.log1p(counts[aid][year]) for year in years] for aid in ids}
    scales = [
        statistics.pstdev(vectors[aid][j] for aid in donors) for j in range(len(years))
    ]
    active = [j for j, scale in enumerate(scales) if scale > 0]
    distances = []
    for aid in sorted(donors):
        distance = (
            statistics.mean(
                ((vectors[aid][j] - vectors[target][j]) / scales[j]) ** 2
                for j in active
            )
            if active
            else 0.0
        )
        distances.append((aid, distance))
    return sorted(distances, key=lambda x: (x[1], x[0]))[:limit], not active


def contrast(target, donors, counts, pre, post):
    ids = [target] + donors
    if any(y not in counts.get(aid, {}) for aid in ids for y in pre + post):
        raise ValueError("incomplete_selected_followup")
    target_pre = statistics.mean(counts[target][y] for y in pre)
    target_post = statistics.mean(counts[target][y] for y in post)
    donor_pre = statistics.mean(counts[aid][y] for aid in donors for y in pre)
    donor_post = statistics.mean(counts[aid][y] for aid in donors for y in post)
    return dict(
        target_pre=target_pre,
        target_post=target_post,
        control_pre=donor_pre,
        control_post=donor_post,
        difference_in_changes=(target_post - target_pre) - (donor_post - donor_pre),
    )


def report_publications(links, units, dates, sources):
    """Bibliographic report years, explicitly distinct from first disclosure."""
    records = []
    for link in links:
        sid = link["source_id"]
        date = dates.get(sid, {})
        year = date.get("stated_date", "")
        if (
            link["relation"] != "assessment_source"
            or not sid.startswith("dp_")
            or len(year) != 4
            or not year.isdigit()
            or not date.get("date_meaning", "").startswith("RePEc current record")
        ):
            continue
        unit = units[link["unit_id"]]
        records.append(
            dict(
                article_id=unit["article_id"],
                unit_id=unit["unit_id"],
                source_id=sid,
                report_publication_year=year,
                date_precision="year",
                date_kind="reported_publication_year_not_first_disclosure",
                source_url=sources[sid]["url"],
                assessment_resolved=unit["assessment_resolved"],
                raw_disposition=unit["disposition"],
            )
        )
    common.unique(records, ["unit_id", "source_id"])
    return records


def build():
    articles = index(read("articles"), "article_id")
    units = read("assessment_inventory")
    index(units, "unit_id")
    unit_index = index(units, "unit_id")
    links = read("assessment_sources")
    sources = index(read("sources"), "source_id")
    source_dates = index(read("source_metadata"), "source_id")
    events = read("events")
    claims = index(read("assessments"), "assessment_id")
    index(events, "event_id")
    grouped = collections.defaultdict(list)
    dated = collections.defaultdict(list)
    for unit in units:
        if unit["article_id"] not in articles:
            raise ValueError("Unknown original in assessment inventory")
        grouped[unit["article_id"]].append(unit)
    for event in events:
        if event["article_id"] not in grouped:
            raise ValueError("Curated event outside assessment roster")
        if event["publicity_verified"] == "yes" and event["year"]:
            if event["date"] and event["date"][:4] != event["year"]:
                raise ValueError("Verified disclosure date/year disagreement")
            if event["date_precision"] not in {"day", "month", "year"}:
                raise ValueError("Disclosure precision does not establish one year")
            dated[event["article_id"]].append(event)
    for aid in dated:
        dated[aid].sort(key=lambda e: (int(e["year"]), e["date"], e["event_id"]))
    publications = report_publications(links, unit_index, source_dates, sources)
    report_dates = collections.defaultdict(list)
    for row in publications:
        report_dates[row["article_id"]].append(row)
    for rows in report_dates.values():
        rows.sort(key=lambda r: (int(r["report_publication_year"]), r["source_id"]))
    counts = {
        "grouped_article_review_works": history(read("grouped/citations")),
        "article_review_edges": history(read("citations")),
        "all_type_annual_totals": history(read("aggregate/citations")),
    }
    logs = index(read("citation_retrieval"), "article_id")
    for aid in list(counts["article_review_edges"]):
        if logs.get(aid, {}).get("status") != "complete":
            del counts["article_review_edges"][aid]
    roster, evidence = [], []
    for aid, assessments in sorted(grouped.items()):
        article = articles[aid]
        verified = dated.get(aid, [])
        event = verified[0] if verified else {}
        roster.append(
            dict(
                article_id=aid,
                title=article["title"],
                doi=article["doi"],
                identity_verified=article["identity_verified"],
                journal=article["journal"],
                journal_id=article["journal_id"],
                original_publication_date=article["publication_date"],
                original_date_source=article["publication_date_source"],
                indexed_publication_year=article["indexed_publication_year"],
                assessment_units=len(assessments),
                resolved_units=sum(
                    u["assessment_resolved"] == "yes" for u in assessments
                ),
                raw_dispositions=";".join(
                    sorted({u["disposition"] for u in assessments})
                ),
                verified_curated_challenge_dates=len(verified),
                first_verified_curated_challenge_year=event.get("year", ""),
                first_verified_curated_challenge_date=event.get("date", ""),
                challenge_date_precision=event.get("date_precision", ""),
                challenge_evidence_url=event.get("date_evidence_url", ""),
                first_i4r_report_publication_year=(
                    report_dates[aid][0]["report_publication_year"]
                    if report_dates.get(aid)
                    else ""
                ),
                grouped_article_review_history=(
                    "complete"
                    if aid in counts["grouped_article_review_works"]
                    else "unavailable"
                ),
                initial_assessment_chronology="pending_review",
                article_review_history=logs.get(aid, {}).get("status", "not_collected"),
                all_type_annual_history=(
                    "available"
                    if aid in counts["all_type_annual_totals"]
                    else "unavailable"
                ),
            )
        )
    for link in links:
        unit, source = unit_index[link["unit_id"]], sources[link["source_id"]]
        date = source_dates.get(link["source_id"], {})
        evidence.append(
            dict(
                unit_id=unit["unit_id"],
                article_id=unit["article_id"],
                source_id=link["source_id"],
                relation=link["relation"],
                source_title=source["title"],
                source_url=source["url"],
                stated_date=date.get("stated_date", ""),
                date_meaning=date.get("date_meaning", ""),
                first_disclosure_status="not_established_by_this_metadata",
            )
        )
    annual = []
    for measure, series in counts.items():
        for aid in sorted(grouped):
            for year, value in sorted(series.get(aid, {}).items()):
                if year <= CUTOFF:
                    annual.append(
                        dict(
                            article_id=aid, measure=measure, year=year, citations=value
                        )
                    )
    controls = index(read("control_articles"), "article_id")
    census_controls = set(controls)
    sampled_pools, sample_members = [], collections.defaultdict(set)
    if (OUT / "comparison_pools.csv").exists():
        sampled_pools = common.read_csv(OUT / "comparison_pools.csv")
        controls.update(
            index(common.read_csv(OUT / "comparison_articles.csv"), "article_id")
        )
        for row in common.read_csv(OUT / "comparison_members.csv"):
            sample_members[row["pool_id"]].add(row["article_id"])
    excluded = {r["article_id"] for r in read("control_exclusions")}
    if (OUT / "comparison_exclusions.csv").exists():
        excluded.update(
            r["article_id"] for r in common.read_csv(OUT / "comparison_exclusions.csv")
        )
    assessed_dois = {a["doi"] for a in articles.values() if a["doi"]}
    assessed_work_ids = {
        a["openalex_id"] for a in articles.values() if a["openalex_id"]
    }
    publisher_dois = {}
    decision_path = OUT / "comparison_metadata_decisions.csv"
    if decision_path.exists():
        publisher_dois = {
            r["article_id"]: r["publisher_doi"] for r in common.read_csv(decision_path)
        }
    assessed_titles = {a["title"].casefold().strip() for a in articles.values()}
    pools = index(read("risk_set_retrieval"), "event_id")
    eligibility, matches, results, paths, balance = [], [], [], [], []
    analysis_events = [
        (aid, verified[0], "verified_curated_challenge")
        for aid, verified in sorted(dated.items())
    ]
    for aid, rows in sorted(report_dates.items()):
        year = rows[0]["report_publication_year"]
        article = articles[aid]
        status = article["retracted"]
        retraction_date = article["retraction_date"]
        already = "no" if status == "no" else "unknown"
        if status == "yes" and retraction_date:
            already = "yes" if int(retraction_date[:4]) <= int(year) else "no"
        analysis_events.append(
            (
                aid,
                dict(
                    event_id="report_publication_" + aid,
                    year=year,
                    already_retracted=already,
                ),
                "i4r_report_publication",
            )
        )
    for aid, event, basis in analysis_events:
        article = articles[aid]
        year = int(event["year"])
        if basis == "verified_curated_challenge":
            assessment_labels = claims[event["assessment_id"]]["category"]
            assessment_resolution = claims[event["assessment_id"]]["error_verified"]
            report_sources = event["source_id"]
        else:
            initial = [
                r
                for r in report_dates[aid]
                if int(r["report_publication_year"]) == year
            ]
            assessment_labels = ";".join(
                sorted({r["raw_disposition"] for r in initial})
            )
            assessment_resolution = (
                "yes"
                if all(r["assessment_resolved"] == "yes" for r in initial)
                else "no"
            )
            report_sources = ";".join(sorted({r["source_id"] for r in initial}))
        pool = next((p for p in pools.values() if pool_covers(p, article)), {})
        pool_kind, allowed = "census", census_controls
        if not pool:
            pool = next((p for p in sampled_pools if pool_covers(p, article)), {})
            pool_kind = "seeded_candidate_sample"
            allowed = sample_members.get(pool.get("event_id", ""), set())
        for window, (before, after) in WINDOWS.items():
            pre = list(range(year - before, year))
            post = list(range(year + 1, year + after + 1))
            for measure, series in counts.items():
                key = dict(
                    article_id=aid,
                    event_id=event["event_id"],
                    event_basis=basis,
                    measure=measure,
                    window=window,
                )
                reasons = []
                if article["identity_verified"] != "yes":
                    reasons.append("original_identity_unverified")
                if not publication_before(article, pre[0]):
                    reasons.append("insufficient_full_baseline_age")
                if post[-1] > CUTOFF:
                    reasons.append("insufficient_complete_followup_years")
                if event["already_retracted"] != "no":
                    reasons.append("original_retraction_status_not_eligible")
                if not article["journal_id"] or not article["indexed_publication_year"]:
                    reasons.append("original_journal_year_missing")
                if pool.get("status") != "complete":
                    reasons.append("journal_pool_not_complete")
                candidates = [
                    c
                    for c in controls.values()
                    if c["article_id"] in allowed
                    and c["journal_id"] == article["journal_id"]
                    and c["indexed_publication_year"]
                    == article["indexed_publication_year"]
                    and c["type"] == article["type"]
                    and c["article_id"] not in excluded
                    and c["doi"] not in assessed_dois
                    and c["openalex_id"] not in assessed_work_ids
                    and publisher_dois.get(c["article_id"], "") not in assessed_dois
                    and c["title"].casefold().strip() not in assessed_titles
                    and donor_retraction_eligible(c, year)
                ]
                if any(
                    c["identity_verified"] != "yes"
                    or not c["publication_date_source"]
                    or not c["publication_date"]
                    for c in candidates
                ):
                    reasons.append("control_identity_or_date_incomplete")
                donors = [
                    c["article_id"]
                    for c in candidates
                    if c["identity_verified"] == "yes" and publication_before(c, pre[0])
                ]
                if not donors:
                    reasons.append("no_eligible_same_journal_year_controls")
                selected, tied = [], False
                if not reasons:
                    try:
                        selected, tied = rank_donors(aid, donors, series, pre)
                    except ValueError as exc:
                        reasons.append(str(exc))
                for y in pre if selected else []:
                    donor_values = [series[c][y] for c in donors]
                    selected_values = [series[c][y] for c, _ in selected]
                    balance.append(
                        key
                        | dict(
                            year=y,
                            target_citations=series[aid][y],
                            selected_control_mean=statistics.mean(selected_values),
                            eligible_pool_min=min(donor_values),
                            eligible_pool_max=max(donor_values),
                            target_outside_pool_range=not min(donor_values)
                            <= series[aid][y]
                            <= max(donor_values),
                            log_baseline_difference=math.log1p(series[aid][y])
                            - statistics.mean(math.log1p(v) for v in selected_values),
                        )
                    )
                for rank, (control, distance) in enumerate(selected, 1):
                    matches.append(
                        key
                        | dict(
                            control_id=control,
                            rank=rank,
                            distance=round(distance, 12),
                            weight=1 / len(selected),
                            constant_baseline_coordinates=tied,
                            later_retraction=controls[control]["retracted"] == "yes",
                        )
                    )
                if not reasons:
                    try:
                        ids = [control for control, _ in selected]
                        values = contrast(aid, ids, series, pre, post)
                        results.append(
                            key
                            | dict(
                                title=article["title"],
                                event_year=year,
                                controls=len(ids),
                                assessment_labels=assessment_labels,
                                assessment_resolved=assessment_resolution,
                                report_sources=report_sources,
                            )
                            | values
                        )
                        for t in range(-before, after + 1):
                            y = year + t
                            paths.append(
                                key
                                | dict(
                                    event_time=t,
                                    year=y,
                                    target_citations=series[aid].get(y, ""),
                                    control_citations=(
                                        statistics.mean(series[c][y] for c in ids)
                                        if all(y in series[c] for c in ids)
                                        else ""
                                    ),
                                )
                            )
                    except ValueError as exc:
                        reasons.append(str(exc))
                eligibility.append(
                    key
                    | dict(
                        pool_kind=pool_kind,
                        pool_receipt_event=pool.get("event_id", ""),
                        pool_query_filter=pool.get("query_filter", ""),
                        same_year_candidates=len(candidates),
                        eligible_controls=len(donors),
                        status=";".join(reasons) or "contrast_available",
                    )
                )

    def write(name, rows, fields=None):
        exported = [
            {
                key: round(value, 12) if isinstance(value, float) else value
                for key, value in row.items()
            }
            for row in rows
        ]
        common.write_csv(OUT / (name + ".csv"), exported, fields or list(rows[0]))

    write("report_publications", publications)
    write("originals", roster)
    write("assessment_date_evidence", evidence)
    write("annual_citations", annual)
    write("eligibility", eligibility)
    keys = ["article_id", "event_id", "event_basis", "measure", "window"]
    write(
        "matches",
        matches,
        keys
        + [
            "control_id",
            "rank",
            "distance",
            "weight",
            "constant_baseline_coordinates",
            "later_retraction",
        ],
    )
    write(
        "balance",
        balance,
        keys
        + [
            "year",
            "target_citations",
            "selected_control_mean",
            "eligible_pool_min",
            "eligible_pool_max",
            "target_outside_pool_range",
            "log_baseline_difference",
        ],
    )
    write(
        "case_contrasts",
        results,
        keys
        + [
            "title",
            "event_year",
            "controls",
            "assessment_labels",
            "assessment_resolved",
            "report_sources",
            "target_pre",
            "target_post",
            "control_pre",
            "control_post",
            "difference_in_changes",
        ],
    )
    write(
        "paths",
        paths,
        keys + ["event_time", "year", "target_citations", "control_citations"],
    )
    summaries = []
    by_group = collections.defaultdict(list)
    for row in results:
        for label in ["all_assessments", row["assessment_labels"]]:
            by_group[row["event_basis"], row["measure"], row["window"], label].append(
                row
            )
    for (basis, measure, window, label), cases in sorted(by_group.items()):
        deltas = [r["difference_in_changes"] for r in cases]
        summaries.append(
            dict(
                event_basis=basis,
                measure=measure,
                window=window,
                assessment_labels=label,
                originals=len(cases),
                mean_change=statistics.mean(deltas),
                median_change=statistics.median(deltas),
                mean_original_pre=statistics.mean(r["target_pre"] for r in cases),
                mean_original_post=statistics.mean(r["target_post"] for r in cases),
                mean_control_pre=statistics.mean(r["control_pre"] for r in cases),
                mean_control_post=statistics.mean(r["control_post"] for r in cases),
            )
        )
    write("descriptive_summary", summaries)
    summary = dict(
        assessment_units=len(units),
        originals=len(roster),
        verified_original_identities=sum(
            r["identity_verified"] == "yes" for r in roster
        ),
        originals_with_publisher_dates=sum(
            bool(r["original_date_source"] and r["original_publication_date"])
            for r in roster
        ),
        originals_with_verified_curated_challenge_dates=len(dated),
        originals_with_i4r_report_publication_years=len(report_dates),
        originals_with_grouped_article_review_histories=sum(
            r["grouped_article_review_history"] == "complete" for r in roster
        ),
        originals_with_complete_article_review_histories=sum(
            r["article_review_history"] == "complete" for r in roster
        ),
        originals_with_all_type_annual_histories=sum(
            r["all_type_annual_history"] == "available" for r in roster
        ),
        contrasts_by_measure_window=dict(
            collections.Counter(
                r["event_basis"] + "/" + r["measure"] + "/" + r["window"]
                for r in results
            )
        ),
    )
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    lines = [
        "# Citation study: current data and comparisons",
        "",
        "Generated from committed snapshots; completed outcome years end in 2025.",
        "",
        f"The roster contains **{len(units)} assessments of {len(roster)} originals**. "
        f"{summary['verified_original_identities']} originals have verified "
        "identities and "
        f"{summary['originals_with_publisher_dates']} have publisher dates. "
        f"Only {len(dated)} currently have verified curated challenge dates; "
        "these do not yet establish the first assessment of every original.",
        "",
        "Article/review citation histories are complete for "
        f"{summary['originals_with_complete_article_review_histories']} originals. "
        "Cached annual totals across all citing document types are available for "
        f"{summary['originals_with_all_type_annual_histories']}. "
        "These are separate measurements and are never combined within a comparison.",
        "",
        f"Grouped article/review counts are available for "
        f"{summary['originals_with_grouped_article_review_histories']} originals; "
        f"{len(report_dates)} originals have a linked I4R report publication year. "
        "Report publication is a separate event from first public criticism.",
        "",
        "## Comparisons around verified curated challenges",
        "",
        "Same-journal, exact indexed-year controls; up to five donors selected on "
        "baseline citations. Missing pool/baseline data block matching. Missing "
        "selected follow-up blocks the contrast. Every exclusion remains in "
        "the eligibility table.",
        "",
        "| Measurement / window | Available case contrasts |",
        "|---|---:|",
    ]
    for measure in counts:
        for window in WINDOWS:
            n = summary["contrasts_by_measure_window"].get(
                "verified_curated_challenge/" + measure + "/" + window, 0
            )
            lines.append(f"| {measure} / {window} | {n} |")
    lines += [
        "",
        "Report-publication comparisons are also retained in the CSVs with "
        "event_basis=i4r_report_publication. They do not identify first disclosure. "
        "These selected-case diagnostics do not estimate an I4R-wide response. "
        "No inferential interval is reported. The primary three-pre/three-post-year "
        "article/review analysis remains incomplete.",
        "",
        "## Next collection work",
        "",
        "Verify report publication and first-public assessment dates in the "
        "full roster; "
        "review native outcome labels; complete citation histories and exact "
        "journal/year "
        "donor pools. OSF creation/current catalog dates are explicitly marked "
        "as leads, "
        "not treated as disclosure dates.",
        "",
        "Outputs: `data/trajectories/originals.csv`, `assessment_date_evidence.csv`, "
        "`annual_citations.csv`, `eligibility.csv`, `matches.csv`, "
        "`case_contrasts.csv`, `balance.csv`, "
        "and `paths.csv`. See [the design](study-design.md).",
    ]
    (common.ROOT / "docs/trajectory-results.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    build()
