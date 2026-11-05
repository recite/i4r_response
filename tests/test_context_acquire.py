"""Retrieval must not turn a downloaded preview into verified full text."""

import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import context_acquire as acquire  # noqa: E402


class Response(io.BytesIO):
    def geturl(self):
        return "https://example.org/article"


class ContextAcquisitionTests(unittest.TestCase):
    def test_duplicate_locations_do_not_duplicate_requests(self):
        work = {
            "locations": [
                {"pdf_url": "http://example.org/a.pdf", "version": "publishedVersion"}
            ]
        }
        self.assertEqual(
            len(
                list(
                    acquire.candidates(work, [("https://example.org/a.pdf", "unknown")])
                )
            ),
            1,
        )

    def test_download_is_only_a_candidate_and_receipt_is_reused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with (
                patch.object(acquire, "ROOT", root),
                patch.object(acquire, "CACHE", root / "cache"),
                patch.object(
                    acquire.urllib.request,
                    "urlopen",
                    return_value=Response(b"<p>Access denied</p>"),
                ) as request,
            ):
                result = acquire.retrieve("W1", "https://example.org/a", "unknown")
                self.assertEqual(result["status"], "retrieved_candidate")
                self.assertEqual(
                    (root / result["text_path"]).read_text(), "Access denied"
                )
                self.assertEqual(
                    result, acquire.retrieve("W1", "https://example.org/a", "unknown")
                )
                self.assertEqual(request.call_count, 1)

    def test_oversized_download_is_not_success(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with (
                patch.object(acquire, "ROOT", root),
                patch.object(acquire, "CACHE", root / "cache"),
                patch.object(acquire, "LIMIT", 4),
                patch.object(
                    acquire.urllib.request, "urlopen", return_value=Response(b"12345")
                ),
            ):
                result = acquire.retrieve("W1", "https://example.org/a", "unknown")
                self.assertEqual(result["status"], "failed")
                self.assertEqual(result["text_path"], "")
