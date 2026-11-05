"""Interrupted collection must not reset the cumulative prepaid cap."""

import json
import math
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import replication_collect as collector  # noqa: E402


class BudgetTests(unittest.TestCase):
    def test_interrupted_runs_reserve_spend_before_dispatch(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            row = dict(article_id="a", role="original")
            balance = [1.0]
            requests = []

            def account():
                return dict(
                    prepaid_remaining_usd=balance[0],
                    daily_remaining_usd=0.0,
                    daily_used_usd=1.0,
                )

            def acquire(item, offline, stopped):
                if stopped.is_set():
                    return [], dict(
                        role="original",
                        article_id="a",
                        detail="response_not_cached",
                        status="unavailable",
                    )
                requests.append(item)
                balance[0] -= 0.0001
                raise RuntimeError("interrupted after a billed request")

            stack.enter_context(patch.object(collector, "OUT", root))
            stack.enter_context(patch.object(collector, "CACHE", root / "cache"))
            stack.enter_context(
                patch.object(collector.grouped, "CACHE", root / "cache")
            )
            stack.enter_context(
                patch.object(collector, "history_roster", return_value=[row])
            )
            stack.enter_context(patch.object(collector, "account", side_effect=account))
            stack.enter_context(
                patch.object(collector.grouped, "query", return_value="query")
            )
            stack.enter_context(
                patch.object(collector.grouped, "acquire", side_effect=acquire)
            )
            stack.enter_context(patch.object(collector.grouped, "validate"))
            stack.enter_context(patch.object(collector.common, "write_csv"))
            for _ in range(6):
                try:
                    collector.collect_histories(fetch=True, max_paid_usd=0.0004)
                except RuntimeError:
                    pass
            self.assertEqual(len(requests), 1)
            ledger = json.loads((root / "collection_cost.json").read_text())
            self.assertAlmostEqual(ledger["unreconciled_paid_reservations"], 0.0004)
            self.assertLessEqual(1.0 - balance[0], 0.0004)

    def test_final_accounting_releases_reservation_only_on_success(self):
        for interrupted in [False, True]:
            with (
                self.subTest(interrupted=interrupted),
                tempfile.TemporaryDirectory() as directory,
                ExitStack() as stack,
            ):
                root = Path(directory)
                row = dict(article_id="a", role="original")
                initial = dict(
                    prepaid_remaining_usd=1.0,
                    daily_remaining_usd=0.0,
                    daily_used_usd=1.0,
                )
                final = (
                    RuntimeError("account unavailable")
                    if interrupted
                    else initial | dict(prepaid_remaining_usd=0.9999)
                )
                for name, value in [("OUT", root), ("CACHE", root / "cache")]:
                    stack.enter_context(patch.object(collector, name, value))
                stack.enter_context(
                    patch.object(collector.grouped, "CACHE", root / "cache")
                )
                stack.enter_context(
                    patch.object(collector, "history_roster", return_value=[row])
                )
                stack.enter_context(
                    patch.object(
                        collector, "account", side_effect=[initial, initial, final]
                    )
                )
                stack.enter_context(
                    patch.object(collector.grouped, "query", return_value="query")
                )

                def acquire(*args):
                    ledger = json.loads((root / "collection_cost.json").read_text())
                    self.assertAlmostEqual(ledger["pending_paid_reservation"], 0.0004)
                    return [], row | dict(detail="", status="complete")

                stack.enter_context(
                    patch.object(collector.grouped, "acquire", side_effect=acquire)
                )
                stack.enter_context(patch.object(collector.grouped, "validate"))
                stack.enter_context(patch.object(collector.common, "write_csv"))
                if interrupted:
                    with self.assertRaisesRegex(RuntimeError, "account unavailable"):
                        collector.collect_histories(fetch=True, max_paid_usd=0.0004)
                else:
                    collector.collect_histories(fetch=True, max_paid_usd=0.0004)
                ledger = json.loads((root / "collection_cost.json").read_text())
                self.assertAlmostEqual(
                    ledger["pending_paid_reservation"], 0.0004 if interrupted else 0
                )
                self.assertAlmostEqual(
                    ledger["provider_reported_prepaid_debit"],
                    0 if interrupted else 0.0001,
                )

    def test_invalid_caps_fail_before_any_account_request(self):
        with patch.object(collector, "account") as account:
            for cap in [-1, math.inf, math.nan]:
                with self.subTest(cap=cap), self.assertRaises(ValueError):
                    collector.collect_histories(fetch=True, max_paid_usd=cap)
            account.assert_not_called()
