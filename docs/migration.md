# Separation from sig_fault

This repository is the development home for the I4R assessment-response study.
The source commit and original code hashes are in migration.json; imported public
data hashes are in imported-data.json. Reviewed evidence and native assessment
labels were preserved. The original source repository has unrelated local edits
to renv/activate.R; they are outside this migration.

The new common.py contains only the shared I/O, identifier, receipt and request
helpers needed by the I4R pipeline. The old citation-context pilot was not copied.
External known-assessment exclusions were frozen into data/external_assessments.csv
with their original source-table paths, removing build dependencies on unrelated
sig_fault cohorts. All ordinary builds use local committed inputs.

Private source material is moved locally, never uploaded. Download receipts retain
original URLs, hashes and retrieval timestamps; the private-data/i4r relative
layout is preserved. Existing evidence and acquisition state are not thrown away
because a ZIP contains large datasets. Public inventory files are not a backup of
the private source bytes. Keep a separate verified backup for long-term retention.

Inherited result files and guides document prior exploratory analyses, not a new
preregistered study. No license is inferred for downloaded third-party documents
or replication packages. The new design is retrospective and its broader novelty
and measurement feasibility remain under review.

The local cache relocation was verified file by file with SHA-256 before and after the move. Aggregate counts are in private-migration.json; the file-level ledger remains private. The external OpenCitations cache stays in sig_fault, and its shared identity and retraction metadata were retained there. These small shared inputs remain necessary for that project’s external-registry checks.
