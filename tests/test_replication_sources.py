"""Check prior-label preservation and candidate timing without estimating effects."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import replication_sources as sources  # noqa: E402


class SourceTests(unittest.TestCase):
    def test_timing_requires_complete_calendar_years(self):
        self.assertEqual(
            sources.timing(dict(year_o="2010", year_r="2013")),
            "passes_year_screen_only",
        )
        self.assertEqual(
            sources.timing(dict(year_o="2011", year_r="2013")),
            "insufficient_full_baseline_age",
        )
        self.assertEqual(
            sources.timing(dict(year_o="2010", year_r="2025")),
            "insufficient_complete_followup_years",
        )
        self.assertEqual(
            sources.timing(dict(year_o="NA", year_r="2020")), "year_missing_or_invalid"
        )

    def test_summary_rows_are_removed_and_fractional_labels_preserved(self):
        row = {
            "url": "https://ideas.repec.org/p/zbw/i4rdps/3.html",
            "narrow replication": "1",
            "robust": "0.75",
            "complete materials for replication": "NA",
        }
        rows = sources.prior_labels(
            [row, {"url": "Mean"}, {"url": ""}], {"dp_003": {"a", "b"}}
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["robustness_score"], "0.75")
        self.assertEqual(rows[0]["materials_score"], "NA")
        self.assertEqual(
            rows[0]["mapping_status"], "multiple_originals_review_required"
        )
        self.assertEqual(rows[0]["linked_original_count"], 2)

    def test_unexpected_urls_fail_instead_of_disappearing(self):
        with self.assertRaisesRegex(ValueError, "Unexpected"):
            sources.prior_labels([{"url": "https://example.org/report"}], {})

    def test_missing_doi_is_not_an_original(self):
        self.assertFalse(sources.present("NA"))
        self.assertFalse(sources.present(""))
        self.assertTrue(sources.present("10.1234/example"))

    def test_non_doi_identifiers_do_not_count_as_verified_doi_pairs(self):
        self.assertEqual(
            sources.doi("https://doi.org/10.1234/Example"), "10.1234/example"
        )
        self.assertEqual(sources.doi("https://www.jstor.org/stable/123"), "")
        self.assertEqual(sources.doi("djaerv_2018"), "")
        self.assertEqual(sources.doi("NA"), "")
