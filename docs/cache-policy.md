# Reference records and disposable caches

The study does not require copies of original replication datasets or environments.
Source identities, hosted URLs, retrieval dates, hashes and file sizes are recorded
in `data/i4r/source_manifest.csv`; archive-member inventories and evidence reviews
are retained separately. Original article DOIs/OpenAlex IDs support citation lookup.

The 62 bulk ZIP caches (4.51 GB) were verified against those receipts and removed.
`archive-cache-pruning.json` records the exact paths. No assessment annotations,
extracted evidence or citation tables were removed. Remaining local PDFs and API
responses are temporary working caches, excluded from Git and unnecessary for
ordinary builds. Retrieve only the particular documents needed for a dated claim
packet or citation-context judgment; do not download whole replication packages.

A URL is a retrieval reference, not a promise of permanent availability or unchanged
content. Recheck the recorded hash on retrieval, record changed versions separately,
and preserve the specific permitted evidence needed to audit each coded judgment.
All full-text availability failures remain explicit missingness.
