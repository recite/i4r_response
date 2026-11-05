"""Numerical and missingness checks for the citation-first study."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import trajectory_basics as study  # noqa: E402


class TrajectoryTests(unittest.TestCase):
    def test_missing_year_is_not_zero(self):
        rows = [dict(article_id="a", year="2020", citations="0", status="complete")]
        series = study.history(rows)
        self.assertEqual(series["a"][2020], 0)
        self.assertNotIn(2021, series["a"])
        with self.assertRaises(ValueError):
            study.history(rows + rows)
        rows[0]["status"] = "incomplete"
        self.assertNotIn("a", study.history(rows))

    def test_missing_donor_baseline_blocks_matching(self):
        counts = {"a": {1: 10, 2: 12}, "b": {1: 9}, "c": {1: 8, 2: 11}}
        with self.assertRaisesRegex(ValueError, "incomplete_baseline"):
            study.rank_donors("a", ["b", "c"], counts, [1, 2])

    def test_post_outcomes_do_not_change_matches(self):
        counts = {"a": {1: 10, 2: 12}, "b": {1: 9, 2: 11}, "c": {1: 1, 2: 2}}
        before = study.rank_donors("a", ["b", "c"], counts, [1, 2], limit=1)
        counts["b"][3] = 100000
        counts["c"][3] = 12
        self.assertEqual(
            before, study.rank_donors("a", ["c", "b"], counts, [1, 2], limit=1)
        )
        self.assertEqual(before[0][0][0], "b")
        with self.assertRaisesRegex(ValueError, "incomplete_selected_followup"):
            study.contrast("a", ["b"], counts, [1, 2], [3])

    def test_contrast_is_difference_of_mean_changes(self):
        counts = {
            "a": {1: 10, 2: 14, 4: 20},
            "b": {1: 8, 2: 12, 4: 13},
            "c": {1: 4, 2: 8, 4: 11},
        }
        result = study.contrast("a", ["b", "c"], counts, [1, 2], [4])
        self.assertEqual(result["target_pre"], 12)
        self.assertEqual(result["control_pre"], 8)
        self.assertEqual(result["difference_in_changes"], 4)

    def test_log_symmetric_donors_tie_despite_float_roundoff(self):
        counts = {"target": {1: 13, 2: 5}, "b": {1: 10, 2: 11}, "a": {1: 10, 2: 2}}
        selected, _ = study.rank_donors("target", ["b", "a"], counts, [1, 2])
        self.assertEqual(selected[0][0], "a")
        self.assertEqual(selected[0][1], selected[1][1])

    def test_constant_baselines_are_flagged_and_deterministic(self):
        counts = {k: {1: 0, 2: 0} for k in ["a", "b", "c"]}
        selected, tied = study.rank_donors("a", ["c", "b"], counts, [1, 2], limit=1)
        self.assertTrue(tied)
        self.assertEqual(selected, [("b", 0)])

    def test_publication_requires_complete_baseline_year(self):
        article = dict(publication_date="2018", publication_date_source="Crossref")
        self.assertFalse(study.publication_before(article, 2018))
        self.assertTrue(study.publication_before(article, 2019))
        article["publication_date_source"] = ""
        self.assertFalse(study.publication_before(article, 2019))

    def test_later_retraction_is_not_a_baseline_exclusion(self):
        self.assertTrue(
            study.donor_retraction_eligible(
                dict(retracted="yes", retraction_date="2024"), 2021
            )
        )
        self.assertFalse(
            study.donor_retraction_eligible(
                dict(retracted="yes", retraction_date="2021"), 2021
            )
        )
        self.assertFalse(
            study.donor_retraction_eligible(
                dict(retracted="yes", retraction_date=""), 2021
            )
        )

    def test_pool_must_cover_journal_year_and_type(self):
        article = dict(
            journal_id="https://openalex.org/S1",
            indexed_publication_year="2020",
            type="article",
        )
        pool = dict(
            status="complete",
            query_filter=(
                "primary_location.source.id:https://openalex.org/S1,"
                "publication_year:2019-2021,type:article"
            ),
        )
        self.assertTrue(study.pool_covers(pool, article))
        self.assertFalse(
            study.pool_covers(pool, article | {"indexed_publication_year": "2022"})
        )
        self.assertFalse(study.pool_covers(pool, article | {"journal_id": "S2"}))
        self.assertFalse(study.pool_covers(pool | {"status": "incomplete"}, article))
