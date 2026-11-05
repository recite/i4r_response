source("scripts/00_config.R")
for (module in c("data.R", "events.R", "matching.R", "analysis.R", "report.R")) {
  source(project_file("R", module))
}
for (path in c(derived_dir, table_dir, figure_dir)) dir.create(path, recursive = TRUE, showWarnings = FALSE)
for (stage in c("01_prepare_data.R", "02_match.R", "03_estimate.R", "04_report.R")) {
  sys.source(project_file("scripts", stage), envir = new.env(parent = globalenv()))
}
