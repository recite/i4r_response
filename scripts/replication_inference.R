source("R/replication.R")
folder <- "data/expansion"
changes <- read.csv(file.path(folder, "analysis_changes.csv"), stringsAsFactors = FALSE)
cases <- read.csv(file.path(folder, "case_contrasts.csv"), stringsAsFactors = FALSE)
for (field in c("later_assessment_in_window", "prior_other_assessment")) {
  changes[[field]] <- replication_boolean(changes[[field]])
}
cases$target_outside_pool_range <- replication_boolean(cases$target_outside_pool_range)
outputs <- list()
diagnostics <- list()
for (window in unique(changes$window)) {
  panel <- changes[changes$window == window, ]
  targets <- panel[panel$target == 1, ]
  sizes <- sort(table(targets$report_cluster), decreasing = TRUE)
  largest <- names(sizes)[1]
  specifications <- list(
    all_eligible = panel,
    omit_largest_report = panel[panel$report_cluster != largest, ],
    no_later_assessment = panel[!panel$later_assessment_in_window, ],
    no_prior_other_assessment = panel[!panel$prior_other_assessment, ]
  )
  supported <- cases$article_id[cases$window == window & !cases$target_outside_pool_range]
  specifications$within_donor_pool_range <- panel[panel$article_id %in% supported, ]
  for (specification in names(specifications)) {
    selected <- specifications[[specification]]
    if (!all(c("successful", "failed") %in% selected$outcome)) next
    result <- replication_fit(selected)
    result$window <- window
    result$specification <- specification
    outputs[[length(outputs) + 1L]] <- result
  }
  donors <- panel[panel$target == 0, ]
  diagnostics[[window]] <- data.frame(
    window = window, originals = nrow(targets), report_clusters = length(sizes),
    largest_report = largest, largest_report_originals = as.integer(sizes[1]),
    largest_report_share = as.integer(sizes[1]) / nrow(targets),
    distinct_controls = length(unique(donors$paper_id)),
    maximum_control_reuse = max(table(donors$paper_id))
  )
}
write.csv(do.call(rbind, outputs), file.path(folder, "att_estimates.csv"), row.names = FALSE)
write.csv(do.call(rbind, diagnostics), file.path(folder, "dependence.csv"), row.names = FALSE)
print(do.call(rbind, outputs))

estimates <- do.call(rbind, outputs)
main <- estimates[estimates$specification == "all_eligible", ]
ledger <- read.csv(file.path(folder, "citation_totals.csv"), stringsAsFactors = FALSE)
budget_stopped <- sum(ledger$detail == "budget_stop")
lines <- c(
  "# Replication outcomes and citations", "",
  paste0("Collection is incomplete: ", budget_stopped,
         " requested histories are recorded as stopped by the spending cap."), "",
  paste("Estimates are mean changes relative to matched journal/year controls,",
        "in citations per original paper per year. The event is first recorded",
        "journal publication of a replication report, not verified first public disclosure."), "",
  "| Window | Source-coded outcome | Originals | Estimate | 95% interval |",
  "|---|---|---:|---:|---:|"
)
for (i in seq_len(nrow(main))) {
  r <- main[i, ]
  window_label <- if (r$window == "balanced_3pre_3post") "3 years before / 3 after" else
    "2 years before / 1 after"
  lines <- c(lines, sprintf(
    "| %s | %s | %d | %+.2f | [%+.2f, %+.2f] |",
    window_label, gsub("_", " ", r$outcome), r$originals, r$estimate, r$lower, r$upper
  ))
}
lines <- c(
  lines, "",
  paste("Intervals use two-way paper/report clustering and condition on the matches",
        "and classifications. Source success criteria vary. Some originals lie outside",
        "the sampled donor pool's baseline citation range, and held-out pre-period",
        "changes are not uniformly zero; these remain provisional matched estimates."), "",
  paste("The complete source roster, exclusions, matching diagnostics, repeated-assessment",
        "sensitivities and individual contrasts are in `data/expansion/`.")
)
writeLines(lines, "docs/historical-results.md")
