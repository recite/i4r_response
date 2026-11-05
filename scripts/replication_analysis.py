"""Match first-recorded replication publication events and export citation contrasts."""

from __future__ import annotations

import collections
import json
import math
import statistics

import collect_grouped_citations as grouped
import common
import trajectory_basics as study

OUT = common.ROOT / "data/expansion"


def write(name, rows, fields):
    rounded = [
        {k: round(v, 12) if isinstance(v, float) else v for k, v in r.items()}
        for r in rows
    ]
    common.write_csv(OUT / (name + ".csv"), rounded, fields)


def report_clusters(events):
    parent = {}

    def root(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for event in events:
        reports = event["reports"].split(";")
        for report in reports[1:]:
            a, b = sorted([root(reports[0]), root(report)])
            parent[b] = a
        root(reports[0])
    return {r["article_id"]: root(r["reports"].split(";")[0]) for r in events}


def build():
    events = [
        r
        for r in common.read_csv(OUT / "events.csv")
        if r["status"] == "candidate_for_matching"
    ]
    annual = common.read_csv(OUT / "citations.csv")
    totals = common.read_csv(OUT / "citation_totals.csv")
    grouped.validate(annual, totals)
    counts = study.history(annual)
    candidates = {
        r["article_id"]: r for r in common.read_csv(OUT / "comparison_articles.csv")
    }
    excluded = {
        r["article_id"] for r in common.read_csv(OUT / "comparison_exclusions.csv")
    }
    pools = {
        (r["journal_id"], r["year"], r["type"]): r
        for r in common.read_csv(OUT / "comparison_pools.csv")
    }
    members = collections.defaultdict(set)
    for r in common.read_csv(OUT / "comparison_members.csv"):
        members[r["pool_id"]].add(r["article_id"])
    clusters = report_clusters(events)
    eligibility, matches, cases, stacked, paths, balance = [], [], [], [], [], []
    for event in events:
        aid, year = event["article_id"], int(event["event_year"])
        pool = pools.get(
            (event["journal_id"], event["indexed_year"], event["type"]), {}
        )
        for window, (before, after) in study.WINDOWS.items():
            key = dict(
                article_id=aid, window=window, outcome=event["outcome"], event_year=year
            )
            pre, post = list(range(year - before, year)), list(
                range(year + 1, year + after + 1)
            )
            reasons = []
            if year + after > 2025:
                reasons.append("insufficient_complete_followup_years")
            if int(event["original_publisher_date"][:4]) >= pre[0]:
                reasons.append("insufficient_full_baseline_age")
            if pool.get("status") != "complete":
                reasons.append("comparison_sample_unavailable")
            donors = sorted(
                c
                for c in members[pool.get("event_id", "")]
                if c not in excluded and study.publication_before(candidates[c], pre[0])
            )
            if not donors:
                reasons.append("no_eligible_controls")
            selected = []
            if not reasons:
                try:
                    selected, tied = study.rank_donors(aid, donors, counts, pre)
                    donor_ids = [c for c, _ in selected]
                    values = study.contrast(aid, donor_ids, counts, pre, post)
                except ValueError as exc:
                    reasons.append(str(exc))
            eligibility.append(
                key
                | dict(
                    pool_id=pool.get("event_id", ""),
                    eligible_controls=len(donors),
                    status=";".join(reasons) or "contrast_available",
                )
            )
            if reasons:
                continue
            later = event["later_assessment_year"]
            flags = dict(
                report_cluster=clusters[aid],
                later_assessment_in_window=bool(later and int(later) <= year + after),
                prior_other_assessment=event["earlier_reproduction"] == "True"
                or event["i4r_overlap"] == "True",
            )
            outside = any(
                not min(counts[c][y] for c in donors)
                <= counts[aid][y]
                <= max(counts[c][y] for c in donors)
                for y in pre
            )
            case = (
                key
                | flags
                | dict(
                    title=event["title"],
                    reports=event["reports"],
                    controls=len(selected),
                    target_outside_pool_range=outside,
                    placebo_change="",
                )
                | values
            )
            holdout = [pre[0] - 2, pre[0] - 1]
            ids = [aid] + donor_ids
            old_enough = int(event["original_publisher_date"][:4]) < holdout[0] and all(
                study.publication_before(candidates[c], holdout[0]) for c in donor_ids
            )
            if old_enough and all(y in counts.get(c, {}) for c in ids for y in holdout):
                case["placebo_change"] = study.contrast(
                    aid, donor_ids, counts, holdout[:1], holdout[1:]
                )["difference_in_changes"]
            cases.append(case)
            for c, distance in selected:
                matches.append(
                    key
                    | dict(
                        control_id=c,
                        distance=distance,
                        weight=1 / len(selected),
                        pool_id=pool["event_id"],
                    )
                )
            for c in ids:
                treated = c == aid
                stacked.append(
                    key
                    | flags
                    | dict(
                        case_id=window + "_" + aid,
                        paper_id=c,
                        target=int(treated),
                        weight=1 if treated else 1 / len(selected),
                        change=statistics.mean(counts[c][y] for y in post)
                        - statistics.mean(counts[c][y] for y in pre),
                    )
                )
            for y in pre:
                balance.append(
                    key
                    | dict(
                        year=y,
                        target_citations=counts[aid][y],
                        control_citations=statistics.mean(
                            counts[c][y] for c in donor_ids
                        ),
                        log_gap=math.log1p(counts[aid][y])
                        - statistics.mean(math.log1p(counts[c][y]) for c in donor_ids),
                    )
                )
            for y in pre + post:
                paths.append(
                    key
                    | dict(
                        event_time=y - year,
                        target_citations=counts[aid][y],
                        control_citations=statistics.mean(
                            counts[c][y] for c in donor_ids
                        ),
                    )
                )
    for name, rows in [
        ("matching_eligibility", eligibility),
        ("matches", matches),
        ("case_contrasts", cases),
        ("analysis_changes", stacked),
        ("balance", balance),
        ("paths", paths),
    ]:
        if not rows:
            raise ValueError("No rows for " + name + "; no estimates exported")
        write(name, rows, list(rows[0]))
    summaries = []
    for window in study.WINDOWS:
        for outcome in ["successful", "failed"]:
            rows = [
                r for r in cases if r["window"] == window and r["outcome"] == outcome
            ]
            if not rows:
                continue
            summaries.append(
                dict(
                    window=window,
                    outcome=outcome,
                    originals=len(rows),
                    reports=len({r["report_cluster"] for r in rows}),
                    mean_change=statistics.mean(
                        r["difference_in_changes"] for r in rows
                    ),
                    median_change=statistics.median(
                        r["difference_in_changes"] for r in rows
                    ),
                    mean_target_pre=statistics.mean(r["target_pre"] for r in rows),
                    mean_target_post=statistics.mean(r["target_post"] for r in rows),
                    mean_control_pre=statistics.mean(r["control_pre"] for r in rows),
                    mean_control_post=statistics.mean(r["control_post"] for r in rows),
                    outside_pool_support=sum(
                        r["target_outside_pool_range"] for r in rows
                    ),
                )
            )
    write("estimates_descriptive", summaries, list(summaries[0]))
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    build()
