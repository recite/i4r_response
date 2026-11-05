# Validation

Local checks on 2026-11-04:

- Black, isort and flake8 passed for all Python code and tests.
- 80 Python numerical, acquisition-integrity and feasibility tests passed.
- Registry reconstruction validated keys and evidence requirements.
- The inherited primary matching sample remained empty; the secondary annual-total analysis reproduced three matched events, and the synthetic checks reproduced two supported cases.
- 32 R assertions passed with no failures, warnings or skips; R lint passed under the inherited lint configuration.
- The new feasibility audit generated 15 candidate claim bundles, 11 with complete cached citation histories, and 49 sampled citing-work pairs. None are completed context ratings; dated atomic-claim packets are pending.
- Independent design review and fixes are recorded in independent-review.md.

The baseline and feasibility builds ran without a private source cache. No original research code in downloaded replication archives was executed. GitHub CI separately exercises Python and R builds.

Clean GitHub runners exposed an omitted ggplot2 dependency and platform differences in formatting targets and CSV line endings. The lockfile now includes the plotting dependency closure, Black has an explicit Python syntax target, and CSV output uses LF consistently.

The source sig_fault repository also passed its full `make check` after removal of the I4R build targets and manuscript appendix, including paper compilation, lint, numerical tests and shared external-registry checks. Its pre-existing renv bootstrap edit was preserved outside the migration commit.
