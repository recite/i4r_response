"""Check the distinction between eligibility, missing acquisition, and zero use."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from feasibility import (  # noqa: E402
    claim_status,
    indexed,
    sample_edges,
    validate_event_coverage,
)


class FeasibilityTests(unittest.TestCase):
    def event(self, **changes):
        return (
            dict(
                error_verified="yes",
                material="yes",
                publicity_verified="yes",
                already_retracted="no",
                year="2023",
            )
            | changes
        )

    def test_recent_disclosures_do_not_supply_a_complete_followup_year(self):
        article = {"identity_verified": "yes"}
        self.assertEqual(
            claim_status(self.event(), article), "candidate_for_context_review"
        )
        self.assertIn(
            "no_complete_post_disclosure_year",
            claim_status(self.event(year="2025"), article),
        )
        self.assertIn(
            "public_disclosure_unverified", claim_status(self.event(year=""), article)
        )

    def test_unresolved_or_nonmaterial_claims_are_not_failed_replications(self):
        status = claim_status(
            self.event(material="unresolved"), {"identity_verified": "yes"}
        )
        self.assertIn("material_error_not_verified", status)

    def test_missing_history_is_distinct_from_a_completed_zero(self):
        self.assertEqual(sample_edges([], "a", 2023, False), ([], None))
        self.assertEqual(sample_edges([], "a", 2023, True), ([], 0))

    def test_sampling_is_order_invariant_and_only_uses_first_post_year(self):
        rows = [
            dict(citing_work_id=f"W{i}", publication_year="2024", type="article")
            for i in range(12)
        ]
        expected = sample_edges(rows, "a", 2023, True)
        self.assertEqual(expected, sample_edges(list(reversed(rows)), "a", 2023, True))
        other = [
            dict(citing_work_id="outside", publication_year="2025", type="article")
        ]
        self.assertEqual(expected, sample_edges(rows + other, "a", 2023, True))
        self.assertEqual(len(expected[0]), 5)
        self.assertEqual(expected[1], 12)

    def test_duplicate_keys_fail_instead_of_silently_overwriting(self):
        with self.assertRaises(ValueError):
            indexed([{"id": "a"}, {"id": "a"}], "id")
        edge = dict(citing_work_id="W1", publication_year="2024", type="article")
        with self.assertRaises(ValueError):
            sample_edges([edge, edge], "a", 2023, True)

    def test_missing_event_cannot_silently_remove_a_claim(self):
        with self.assertRaises(ValueError):
            validate_event_coverage([{"assessment_id": "a"}], {"a": {}, "b": {}})
        validate_event_coverage([{"assessment_id": "a"}], {"a": {}})
