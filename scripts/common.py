"""Shared source receipts, identifiers, and tabular I/O."""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def normalize_doi(value):
    return re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", value.strip().lower())


def unique(rows, fields):
    keys = [tuple(row[field] for field in fields) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError(f"Duplicate key: {fields}")


def openalex_api_key():
    """Load credentials from the environment or the user's private config."""
    key = os.environ.get("OPENALEX_API_KEY", "").strip()
    if key:
        return key
    config = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    path = config / "openalex" / "api_key"
    if not path.is_file():
        return None
    return path.read_text().strip() or None


def request(url, path, json_response=True):
    """Cache successful responses; never print or persist authentication tokens."""
    path = Path(path)
    if path.exists():
        payload = path.read_bytes()
        return json.loads(payload) if json_response else payload
    headers = {"User-Agent": "i4r-response-research/0.1"}
    key = openalex_api_key()
    if key and urllib.parse.urlparse(url).hostname == "api.openalex.org":
        headers["Authorization"] = f"Bearer {key}"
    for attempt in range(4):
        try:
            with urllib.request.urlopen(
                urllib.request.Request(url, headers=headers), timeout=30
            ) as response:
                payload = response.read()
            parsed = json.loads(payload) if json_response else payload
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            manifest = {
                "url": url,
                "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "sha256": sha256(payload),
                "bytes": len(payload),
            }
            path.with_suffix(path.suffix + ".source.json").write_text(
                json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
            )
            return parsed
        except urllib.error.HTTPError as error:
            if error.code not in {429, 500, 502, 503, 504} or attempt == 3:
                raise
            time.sleep(min(2 ** (attempt + 1), 8))
        except (TimeoutError, urllib.error.URLError):
            if attempt == 3:
                raise
            time.sleep(2**attempt)
    raise RuntimeError("Request attempts exhausted")


def api_url(endpoint, **params):
    return "https://api.openalex.org/" + endpoint + "?" + urllib.parse.urlencode(params)
