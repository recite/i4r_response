PYTHON ?= python3
RSCRIPT ?= Rscript --vanilla

.PHONY: check lint test registry feasibility trajectories baseline check-r restore-r
check: lint test registry feasibility trajectories
lint:
	$(PYTHON) -m black --check scripts tests
	$(PYTHON) -m isort --check-only scripts tests
	$(PYTHON) -m flake8 scripts tests
test:
	$(PYTHON) -m unittest discover -s tests
registry:
	$(PYTHON) scripts/i4r_registry.py build
	$(PYTHON) scripts/i4r_registry.py validate
feasibility:
	$(PYTHON) scripts/feasibility.py
trajectories: registry
	$(PYTHON) scripts/collect_grouped_citations.py --validate
	$(PYTHON) scripts/trajectory_basics.py
baseline: registry
	$(PYTHON) scripts/i4r_match.py
	$(RSCRIPT) scripts/i4r_analysis.R
	$(PYTHON) scripts/i4r_aggregate.py validate
	$(PYTHON) scripts/i4r_match.py --citation-file data/i4r/aggregate/citations.csv --output-dir data/i4r/aggregate
	$(RSCRIPT) scripts/i4r_analysis.R data/i4r/aggregate docs/i4r/aggregate-results.md
	$(PYTHON) scripts/i4r_synthetic.py
	$(PYTHON) scripts/i4r_report.py
check-r: baseline
	$(RSCRIPT) -e 'testthat::test_dir("tests/testthat", stop_on_failure = TRUE)'
	$(RSCRIPT) -e 'l <- unlist(lapply(c("R", "scripts", "tests/testthat"), lintr::lint_dir), recursive = FALSE); print(l); quit(status = as.integer(length(l) > 0))'
restore-r:
	$(RSCRIPT) -e 'if (!requireNamespace("renv", quietly = TRUE)) install.packages("renv", repos = "https://cloud.r-project.org"); renv::restore(lockfile = "renv.lock", library = Sys.getenv("R_LIBS_USER"), prompt = FALSE)'
