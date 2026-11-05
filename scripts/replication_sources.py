"""Import prior I4R coding and a pinned FLoRA release for sample expansion.

This is a candidate roster, not an estimation sample. Bibliographic years do not
establish when results first became public. Published source labels are retained;
no success/failure labels are inferred from citation outcomes.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import re
import subprocess

import common

OUT = common.ROOT / "data/expansion"
CACHE = common.ROOT / "private-data/expansion"
SOURCES = {
    "flora": (
        "forrtproject/flora-validation",
        "fceed20eaee6c38411ab9972af90353312685136",
        "output/flora.csv",
    ),
    "prior_i4r": (
        "recite/i4replication",
        "8d2d94cc38b65c1930b48daeeca71628ea3bb384",
        "replication_of_specific_studies_coded.csv",
    ),
}
FLORA_FIELDS = [
    "id",
    "doi_o",
    "alt_identifier_o",
    "title_o",
    "journal_o",
    "year_o",
    "doi_r",
    "alt_identifier_r",
    "title_r",
    "journal_r",
    "year_r",
    "type",
    "source",
    "outcome",
    "outcome_quote_source",
    "outcome_computation",
    "outcome_robustness",
    "oa_work_id_o",
    "oa_work_id_r",
]


def fetch():
    CACHE.mkdir(parents=True, exist_ok=True)
    for name, (repo, revision, file) in SOURCES.items():
        endpoint = f"repos/{repo}/contents/{file}?ref={revision}"
        payload = subprocess.check_output(
            ["gh", "api", "-H", "Accept: application/vnd.github.raw+json", endpoint]
        )
        path = CACHE / f"{name}.csv"
        path.write_bytes(payload)
        path.with_suffix(".source.json").write_text(
            json.dumps(
                dict(
                    source=name,
                    repository=repo,
                    revision=revision,
                    url=f"https://github.com/{repo}/blob/{revision}/{file}",
                    sha256=common.sha256(payload),
                    bytes=len(payload),
                    retrieved_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                ),
                indent=2,
            )
            + "\n"
        )


def year(value):
    return int(value) if re.fullmatch(r"[12][0-9]{3}", value) else None


def present(value):
    return value.strip() not in {"", "NA"}


def timing(row):
    original, replication = year(row["year_o"]), year(row["year_r"])
    if original is None or replication is None:
        return "year_missing_or_invalid"
    reasons = []
    if original >= replication - 2:
        reasons.append("insufficient_full_baseline_age")
    if replication + 1 > 2025:
        reasons.append("insufficient_complete_followup_years")
    return ";".join(reasons) or "passes_year_screen_only"


def prior_labels(rows, links):
    output = []
    for row in rows:
        match = re.search(r"/([0-9]+)\.html$", row["url"])
        if not match:
            if row["url"] in {"", "Mean"}:
                continue
            raise ValueError("Unexpected prior-coding URL: " + row["url"])
        sid = f"dp_{int(match.group(1)):03d}"
        targets = sorted(links.get(sid, set()))
        output.append(
            dict(
                source_id=sid,
                source_url=row["url"],
                computational_score=row["narrow replication"],
                robustness_score=row["robust"],
                materials_score=row["complete materials for replication"],
                linked_originals=";".join(targets),
                linked_original_count=len(targets),
                mapping_status=(
                    "one_original"
                    if len(targets) == 1
                    else (
                        "multiple_originals_review_required"
                        if targets
                        else "no_assessment_link"
                    )
                ),
            )
        )
    common.unique(output, ["source_id"])
    return output


def build():
    inputs, receipts = {}, []
    for name in SOURCES:
        path = CACHE / f"{name}.csv"
        receipt = json.loads(path.with_suffix(".source.json").read_text())
        repo, revision, file = SOURCES[name]
        if (
            receipt["repository"] != repo
            or receipt["revision"] != revision
            or receipt["sha256"] != common.sha256(path.read_bytes())
        ):
            raise ValueError("Source receipt mismatch: " + name)
        inputs[name] = common.read_csv(path)
        receipts.append(receipt)
    data = common.ROOT / "data/i4r"
    units = {
        r["unit_id"]: r for r in common.read_csv(data / "assessment_inventory.csv")
    }
    links = collections.defaultdict(set)
    for row in common.read_csv(data / "assessment_sources.csv"):
        if row["relation"] == "assessment_source":
            links[row["source_id"]].add(units[row["unit_id"]]["article_id"])
    prior = prior_labels(inputs["prior_i4r"], links)
    common.write_csv(OUT / "prior_i4r_labels.csv", prior, list(prior[0]))
    assessed = {r["doi"] for r in common.read_csv(data / "articles.csv") if r["doi"]}
    rows = []
    for raw in inputs["flora"]:
        row = {k: raw[k] for k in FLORA_FIELDS}
        row.update(
            year_screen=timing(raw),
            original_in_i4r=common.normalize_doi(raw["doi_o"]) in assessed,
            doi_pair_available=present(raw["doi_o"]) and present(raw["doi_r"]),
            date_review_required=True,
            registry_record="registr" in raw["journal_r"].lower(),
        )
        rows.append(row)
    common.unique(rows, ["id"])
    common.write_csv(OUT / "flora_candidates.csv", rows, list(rows[0]))
    counts = collections.Counter((r["type"], r["year_r"], r["outcome"]) for r in rows)
    annual = [
        dict(assessment_type=t, report_year=y, source_outcome=o, pairs=n)
        for (t, y, o), n in sorted(counts.items())
    ]
    common.write_csv(OUT / "pairs_by_year.csv", annual, list(annual[0]))
    common.write_csv(OUT / "source_snapshots.csv", receipts, list(receipts[0]))
    summarize()


def summarize():
    rows = common.read_csv(OUT / "flora_candidates.csv")
    common.unique(rows, ["id"])
    reps = [r for r in rows if r["type"] == "replication"]
    eligible = [r for r in reps if r["year_screen"] == "passes_year_screen_only"]

    def original_count(rs):
        return len({r["doi_o"] for r in rs if present(r["doi_o"])})

    prior = common.read_csv(OUT / "prior_i4r_labels.csv")
    summary = dict(
        source_pairs=len(rows),
        replication_pairs=len(reps),
        replication_original_dois=original_count(reps),
        replication_year_screen_pairs=len(eligible),
        replication_year_screen_original_dois=original_count(eligible),
        year_screen_outcomes=dict(
            sorted(collections.Counter(r["outcome"] for r in eligible).items())
        ),
        year_screen_binary_outcome_original_dois=original_count(
            [r for r in eligible if r["outcome"] in {"successful", "failed"}]
        ),
        replication_original_dois_overlapping_i4r=original_count(
            [r for r in reps if r["original_in_i4r"] == "True"]
        ),
        prior_coded_reports=len(prior),
        prior_mapping_status=dict(
            sorted(collections.Counter(r["mapping_status"] for r in prior).items())
        ),
        qualification=(
            "Candidate records only; dates, identities, outcomes and repeated "
            "attempts require review before estimation."
        ),
    )
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["fetch", "build", "summarize"])
    args = parser.parse_args()
    {"fetch": fetch, "build": build, "summarize": summarize}[args.command]()
