project_root <- rprojroot::find_root(rprojroot::has_file("DESCRIPTION"))
project_file <- function(...) file.path(project_root, ...)
source_dir <- project_file("data", "raw", "replications")
i4r_dir <- project_file("data", "raw", "i4r")
derived_dir <- project_file("data", "derived")
table_dir <- project_file("tabs")
figure_dir <- project_file("figs")
cache_dir <- project_file("private-data", "replications")
last_citation_year <- 2025L
comparison_seed <- 20261028L
comparison_sample_size <- 20L
analysis_windows <- list(
  five_year = c(before = 5L, after = 3L), three_year = c(before = 3L, after = 3L),
  short = c(before = 2L, after = 1L)
)
