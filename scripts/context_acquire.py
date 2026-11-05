"""Retrieve only texts in the frozen citation-context sample, with receipts."""

import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import subprocess
import urllib.error
import urllib.parse
import urllib.request

from bs4 import BeautifulSoup
from common import ROOT, read_csv, write_csv

CACHE = ROOT / "private-data" / "context"
OUTPUT = ROOT / "data" / "context"
LIMIT = 20 * 1024 * 1024


def candidates(work, extra):
    urls = []
    for location in work.get("locations", []):
        url = location.get("pdf_url")
        if url:
            urls.append((url, location.get("version") or "unknown"))
    urls.extend(extra)
    seen = set()
    for url, version in urls:
        if url.startswith("http://"):
            url = "https://" + url[7:]
        if url not in seen:
            seen.add(url)
            yield url, version


def retrieve(work_id, url, version):
    digest = hashlib.sha256(url.encode()).hexdigest()[:12]
    directory = CACHE / "texts"
    directory.mkdir(parents=True, exist_ok=True)
    stem = directory / f"{work_id}_{digest}"
    receipt_path = stem.with_suffix(".json")
    if receipt_path.exists():
        return json.loads(receipt_path.read_text())
    row = {
        "citing_work_id": "https://openalex.org/" + work_id,
        "url": url,
        "version": version,
        "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "failed",
        "path": "",
        "text_path": "",
        "sha256": "",
        "bytes": "",
        "error": "",
    }
    try:
        request = urllib.request.Request(
            url, headers={"User-Agent": "i4r-response-research/0.1"}
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read(LIMIT + 1)
            row["final_url"] = response.geturl()
        if len(body) > LIMIT:
            raise ValueError("Document exceeds 20 MiB limit")
        suffix = ".pdf" if body.startswith(b"%PDF-") else ".html"
        path = stem.with_suffix(suffix)
        text_path = stem.with_suffix(".txt")
        path.write_bytes(body)
        if suffix == ".pdf":
            subprocess.run(
                ["pdftotext", "-layout", str(path), str(text_path)],
                check=True,
                capture_output=True,
                timeout=30,
            )
        else:
            soup = BeautifulSoup(body, "html.parser")
            for element in soup(["script", "style", "nav", "header", "footer"]):
                element.decompose()
            text_path.write_text(soup.get_text("\n", strip=True))
        row.update(
            status="retrieved_candidate",
            path=str(path.relative_to(ROOT)),
            text_path=str(text_path.relative_to(ROOT)),
            sha256=hashlib.sha256(body).hexdigest(),
            bytes=len(body),
        )
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        row["error"] = type(error).__name__ + ": " + str(error)
    receipt_path.write_text(json.dumps(row, indent=2) + "\n")
    return row


def collect(work_id, extras):
    work = json.loads((CACHE / "metadata" / (work_id + ".json")).read_text())
    rows = [
        retrieve(work_id, url, version) for url, version in candidates(work, extras)
    ]
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    queue = read_csv(ROOT / "data/feasibility/context_review_queue.csv")
    extras = {}
    source_path = OUTPUT / "additional_sources.csv"
    if source_path.exists():
        for row in read_csv(source_path):
            extras.setdefault(row["citing_work_id"].rsplit("/", 1)[-1], []).append(
                (row["url"], row["version"])
            )
    ids = [row["citing_work_id"].rsplit("/", 1)[-1] for row in queue]
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        jobs = {pool.submit(collect, wid, extras.get(wid, [])): wid for wid in ids}
        for future in concurrent.futures.as_completed(jobs):
            rows = future.result()
            results.extend(rows)
            print(jobs[future], [row["status"] for row in rows], flush=True)
    fields = [
        "citing_work_id",
        "url",
        "version",
        "retrieved_at",
        "status",
        "path",
        "text_path",
        "sha256",
        "bytes",
        "error",
        "final_url",
    ]
    results.sort(key=lambda row: (row["citing_work_id"], row["url"]))
    for row in results:
        row.setdefault("final_url", "")
    write_csv(OUTPUT / "retrieval_attempts.csv", results, fields)


if __name__ == "__main__":
    main()
