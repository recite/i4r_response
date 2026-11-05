"""Check grouped-count completeness, sampled pools and date provenance."""

import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import collect_comparison_pools as pools  # noqa: E402
import collect_grouped_citations as grouped  # noqa: E402
import i4r_registry as registry  # noqa: E402
import i4r_sources as sources  # noqa: E402
import trajectory_basics as study  # noqa: E402


class GroupedTests(unittest.TestCase):
    def test_complete_zero_is_valid_but_missing_bins_are_not(self):
        self.assertEqual(
            grouped.grouped_counts({"group_by": [], "meta": {"count": 0}}), ({}, 0)
        )
        with self.assertRaisesRegex(ValueError, "reconcile"):
            grouped.grouped_counts(
                {"group_by": [{"key": "2020", "count": 2}], "meta": {"count": 3}}
            )

    def test_duplicate_unknown_negative_and_future_bins_fail(self):
        for bins in [
            [{"key": "2020", "count": 1}] * 2,
            [{"key": "-111", "count": 1}],
            [{"key": "2020", "count": -1}],
            [{"key": "2026", "count": 1}],
        ]:
            with self.assertRaises(ValueError):
                grouped.grouped_counts({"group_by": bins, "meta": {"count": 2}})

    def test_distributed_history_reconciles_and_missing_year_is_not_zero(self):
        annual = [dict(article_id="a", year=2025, citations=2, status="complete")]
        receipt = dict(
            article_id="a",
            status="complete",
            panel_first_year=2025,
            indexed_publication_year=2025,
            api_count=2,
            sum_counts=2,
            before_publication=0,
        )
        grouped.validate(annual, [receipt])
        with self.assertRaisesRegex(ValueError, "missing_or_extra"):
            grouped.validate([], [receipt])
        with self.assertRaisesRegex(ValueError, "does_not_reconcile"):
            grouped.validate(annual, [receipt | {"api_count": 3}])
        with self.assertRaisesRegex(ValueError, "unavailable_history"):
            grouped.validate(annual, [receipt | {"status": "unavailable"}])

    def test_offline_miss_is_not_a_zero_history(self):
        row = dict(
            article_id="a",
            role="original",
            work_ids="W1",
            indexed_publication_year="2020",
            identity_verified="yes",
        )
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(grouped, "CACHE", Path(folder)),
        ):
            annual, total = grouped.acquire(row, True, threading.Event())
        self.assertEqual(annual, [])
        self.assertEqual(total["status"], "unavailable")
        self.assertEqual(total["api_count"], "")

    def test_observed_pre_indexed_citations_keep_their_years(self):
        import common

        row = dict(
            article_id="a",
            role="original",
            work_ids="W1",
            indexed_publication_year="2020",
            identity_verified="yes",
        )
        payload = {
            "group_by": [{"key": "2018", "count": 2}, {"key": "2020", "count": 3}],
            "meta": {"count": 5},
        }
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(grouped, "CACHE", Path(folder)),
            patch.object(common, "ROOT", Path(folder)),
        ):
            url = grouped.query(row)
            path = Path(folder) / (common.sha256(url.encode()) + ".json")
            path.write_text(json.dumps(payload))
            path.with_suffix(".json.source.json").write_text(
                json.dumps(
                    dict(
                        url=url,
                        sha256=common.sha256(path.read_bytes()),
                        retrieved_at="2026-11-05",
                    )
                )
            )
            annual, total = grouped.acquire(row, True, threading.Event())
        self.assertEqual(annual[0]["year"], 2018)
        self.assertEqual(annual[0]["citations"], 2)
        self.assertTrue(annual[0]["pre_indexed_publication"])
        self.assertEqual(total["before_publication"], 2)
        self.assertEqual(sum(r["citations"] for r in annual), 5)

    def test_sampled_aliases_are_unioned_before_counting(self):
        import common

        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(common, "ROOT", Path(folder)),
            patch.object(sources, "read", return_value=[]),
        ):
            directory = Path(folder) / "data/trajectories"
            row = dict(article_id="c", doi="10.1/c", openalex_id="W1")
            common.write_csv(directory / "comparison_articles.csv", [row], list(row))
            members = [
                dict(article_id="c", openalex_id="W1"),
                dict(article_id="c", openalex_id="W2"),
            ]
            common.write_csv(
                directory / "comparison_members.csv", members, list(members[0])
            )
            records = grouped.roster()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["work_ids"], "W1|W2")


class PoolTests(unittest.TestCase):
    def article(self):
        return dict(journal_id="S1", indexed_publication_year="2020", type="article")

    def work(self, i):
        return dict(
            id=f"W{i}",
            publication_year=2020,
            type="article",
            primary_location={"source": {"id": "S1"}},
        )

    def test_complete_sample_is_not_a_complete_pool(self):
        payloads = [
            {"meta": {"count": 30}},
            {"results": [self.work(i) for i in range(20)]},
        ]
        with patch.object(sources, "fetch", side_effect=payloads) as fetch:
            row, works = pools.sample_pool(self.article(), False)
        self.assertEqual(row["status"], "complete")
        self.assertFalse(row["complete_pool"])
        self.assertEqual(len(works), 20)
        self.assertIn("sample=20", fetch.call_args.args[0])
        self.assertIn("seed=20261028", fetch.call_args.args[0])

    def test_truncated_sample_cannot_be_matched(self):
        with patch.object(
            sources,
            "fetch",
            side_effect=[
                {"meta": {"count": 20}},
                {"results": [self.work(i) for i in range(19)]},
            ],
        ):
            row, works = pools.sample_pool(self.article(), False)
        self.assertEqual(row["status"], "unavailable")
        self.assertEqual(works, [])


class DateTests(unittest.TestCase):
    def test_report_dates_exclude_creation_dates_and_aggregate_links(self):
        unit = dict(
            article_id="a",
            unit_id="u",
            assessment_resolved="yes",
            disposition="favorable",
        )
        links = [
            dict(unit_id="u", source_id="dp_001", relation="assessment_source"),
            dict(unit_id="u", source_id="dp_002", relation="aggregate_context"),
            dict(unit_id="u", source_id="report_1", relation="assessment_source"),
        ]
        dates = {
            "dp_001": dict(
                stated_date="2023", date_meaning="RePEc current record publication date"
            ),
            "dp_002": dict(
                stated_date="2022", date_meaning="RePEc current record publication date"
            ),
            "report_1": dict(stated_date="2020", date_meaning="OSF creation"),
        }
        src = {k: dict(url="https://example.org/" + k) for k in dates}
        rows = study.report_publications(links, {"u": unit}, dates, src)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["report_publication_year"], "2023")
        self.assertEqual(
            rows[0]["date_kind"], "reported_publication_year_not_first_disclosure"
        )

    def test_version_conflict_does_not_replace_identity_or_abort_roster(self):
        title = "An empirical study of schooling and wages"
        aid = registry.article_id(title)
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(sources, "ROOT", Path(folder)),
            patch.object(sources, "DATA", Path(folder) / "data"),
            patch.object(sources, "CACHE", Path(folder) / "private-data"),
        ):
            sources.write(
                "sources.csv",
                [dict(source_id="s", title=title, collection="reports")],
                sources.SOURCE_FIELDS,
            )
            decision = dict(
                article_id=aid,
                title=title,
                doi="10.1/published",
                evidence="fixture",
                source_url="https://example.org",
            )
            sources.write("identity_decisions.csv", [decision], list(decision))
            path = sources.CACHE / "identities" / (aid + ".json")
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(dict(id="W1", doi="10.1/preprint", title=title)))
            registry.build(refresh_metadata=True)
            rebuilt = sources.read("articles.csv")[0]
            self.assertEqual(rebuilt["doi"], "10.1/published")
            self.assertEqual(rebuilt["openalex_id"], "")
            self.assertEqual(
                sources.read("metadata_conflicts.csv")[0]["reason"],
                "doi_or_version_conflict",
            )
