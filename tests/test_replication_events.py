"""Check chronology, metadata completeness and report dependence before estimation."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import replication_analysis as analysis  # noqa: E402
import replication_events as events  # noqa: E402
import replication_metadata as metadata  # noqa: E402


class EventTests(unittest.TestCase):
    def row(self, number, year, outcome):
        return dict(
            id=str(number), doi_r=f"10.1234/{number}", year_r=str(year), outcome=outcome
        )

    def meta(self, number, year):
        return {
            f"10.1234/{number}": dict(
                publisher_date=str(year), publisher_type="journal-article"
            )
        }

    def test_earlier_mixed_is_not_replaced_by_later_failure(self):
        rows = [self.row(1, 2010, "mixed"), self.row(2, 2015, "failed")]
        result = events.first_event(rows, self.meta(1, 2010) | self.meta(2, 2015))
        self.assertEqual(result["outcome"], "mixed")
        self.assertEqual(result["event_year"], 2010)
        self.assertEqual(result["later_assessment_year"], 2015)

    def test_unverified_earlier_report_blocks_chronology(self):
        rows = [self.row(1, 2010, "mixed"), self.row(2, 2015, "failed")]
        result = events.first_event(rows, self.meta(2, 2015))
        self.assertEqual(
            result["chronology_status"], "earlier_or_same_year_unverified_report"
        )

    def test_same_year_disagreement_is_mixed(self):
        rows = [self.row(1, 2010, "successful"), self.row(2, 2010, "failed")]
        result = events.first_event(rows, self.meta(1, 2010) | self.meta(2, 2010))
        self.assertEqual(result["outcome"], "mixed")
        self.assertEqual(result["reports"], "10.1234/1;10.1234/2")

    def test_connected_reports_share_one_cluster(self):
        rows = [
            dict(article_id="a", reports="r1;r2"),
            dict(article_id="b", reports="r2;r3"),
            dict(article_id="c", reports="r4"),
        ]
        clusters = analysis.report_clusters(rows)
        self.assertEqual(clusters["a"], clusters["b"])
        self.assertNotEqual(clusters["a"], clusters["c"])

    def test_batch_conflicts_and_truncation_cannot_promote_identity(self):
        work = dict(doi="10.1234/a", id="W1")
        with self.assertRaisesRegex(ValueError, "multiple"):
            metadata.openalex_batch(
                dict(meta=dict(count=2), results=[work, work | {"id": "W2"}]),
                ["10.1234/a"],
            )
        with self.assertRaisesRegex(ValueError, "truncated"):
            metadata.openalex_batch(
                dict(meta=dict(count=2), results=[work]), ["10.1234/a"]
            )
        self.assertEqual(
            metadata.openalex_batch(
                dict(meta=dict(count=1), results=[work]), ["10.1234/a"]
            ),
            {"10.1234/a": work},
        )
