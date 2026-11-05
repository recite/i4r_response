.PHONY: restore analysis format lint test check paper manuscript ci-docker clean

restore:
	Rscript --vanilla -e 'if (!requireNamespace("renv", quietly = TRUE)) install.packages("renv", repos = "https://cloud.r-project.org"); renv::load(project = getwd()); renv::restore(prompt = FALSE)'

analysis:
	Rscript scripts/99_run_all.R

format:
	Rscript -e 'styler::style_dir("R"); styler::style_dir("scripts"); styler::style_dir("tests")'

lint:
	Rscript -e 'l <- unlist(lapply(c("R", "scripts", "tests"), lintr::lint_dir), recursive = FALSE); print(l); quit(status = as.integer(length(l) > 0))'

test: analysis
	Rscript -e 'testthat::test_dir("tests/testthat", stop_on_failure = TRUE)'

manuscript:
	cd ms && latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex

paper: analysis
	$(MAKE) manuscript

check: lint test
	$(MAKE) manuscript

ci-docker:
	docker run --rm -v "$(CURDIR):/project" -w /project \
		-v r_renv_cache:/root/.cache/R/renv \
		-e RENV_CONFIG_REPOS_OVERRIDE=https://packagemanager.posit.co/cran/latest \
		rocker/r-ver:4.6.0 bash -c "apt-get update && apt-get install -y --no-install-recommends texlive-xetex texlive-latex-extra texlive-fonts-recommended latexmk && make restore check"

clean:
	Rscript --vanilla -e 'unlink("data/derived", recursive = TRUE)'
