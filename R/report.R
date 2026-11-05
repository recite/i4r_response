write_results <- function(prepared, matched, results) {
  events <- prepared$registry$events
  eligible <- events[events$status == "candidate_for_matching", ]
  counts <- table(eligible$outcome)
  main <- results$estimates[results$estimates$specification == "all_eligible", ]
  three_year <- main[main$window == "three_year" & main$outcome == "failed_minus_successful", ]
  short <- main[main$window == "short" & main$outcome == "failed_minus_successful", ]
  stopped <- sum(prepared$inputs$citation_totals$detail == "budget_stop")
  lines <- c(
    "# Citation responses to replication assessments", "",
    sprintf(
      paste(
        "The three-year comparison includes **%s originals**. The failed-minus-successful contrast",
        "is **%+.2f citations per paper per year**, with a 95%% interval of **[%.2f, %.2f]**."
      ),
      three_year$originals, three_year$estimate, three_year$lower, three_year$upper
    ), "",
    sprintf(
      paste(
        "The roster has %s originals eligible for matching: %s source-coded successful and %s",
        "failed replications. The shorter window has %s completed comparisons. The windows overlap;",
        "their sample sizes must not be added."
      ),
      nrow(eligible), counts["successful"], counts["failed"], short$originals
    ), "",
    "| Window | Replication outcome | Originals | Matched change/year | 95% interval |",
    "|---|---|---:|---:|---|"
  )
  for (i in seq_len(nrow(main))) {
    row <- main[i, ]
    lines <- c(lines, sprintf(
      "| %s | %s | %s | %+.2f | [%+.2f, %+.2f] |",
      if (row$window == "three_year") "3 before / 3 after" else "2 before / 1 after",
      gsub("_", " ", row$outcome), row$originals, row$estimate, row$lower, row$upper
    ))
  }
  support <- results$descriptive[results$descriptive$window == "three_year", ]
  lines <- c(
    lines, "", "![Matched citation changes and uncertainty](../figs/replication_estimates.png)", "",
    sprintf(
      paste(
        "Collection is incomplete: %s requested histories remain unavailable under the spending",
        "cap. Of the %s three-year originals, %s lie outside their sampled comparison pool's",
        "baseline citation range. Held-out pre-period changes also differ from zero. These",
        "diagnostics weaken a causal interpretation."
      ),
      stopped, three_year$originals, sum(support$outside_support)
    ), "",
    paste(
      "The event is the first recorded journal publication of a replication report, not verified",
      "first public disclosure. Source success criteria vary. Citation counts measure attention,",
      "not agreement. The difference between the two estimates is not the causal effect of",
      "failing rather than succeeding."
    ), "",
    paste(
      "Intervals use two-way paper/report clustering, conditional on matches and classifications.",
      "See [the design](study_design.md), [source data](../data/README.md), and [estimates and",
      "diagnostics](../tabs/)."
    )
  )
  writeLines(lines, project_file("docs", "results.md"))
  readme_path <- project_file("README.md")
  readme <- readLines(readme_path)
  begin <- match("<!-- results:start -->", readme)
  end <- match("<!-- results:end -->", readme)
  if (is.na(begin) || is.na(end) || begin >= end) stop("README result markers are missing")
  headline <- sprintf(paste(
    "The current analysis includes **%s three-year comparisons** and **%s shorter-window comparisons**.",
    "Collection is incomplete, and matching diagnostics limit causal interpretation."
  ), three_year$originals, short$originals)
  writeLines(c(readme[seq_len(begin)], headline, readme[seq.int(end, length(readme))]), readme_path)
  plot_data <- main[main$window == "three_year", ]
  plot_data$label <- factor(plot_data$outcome,
    levels = rev(c("successful", "failed", "failed_minus_successful")),
    labels = rev(c("Successful", "Failed", "Failed minus successful"))
  )
  figure <- ggplot2::ggplot(plot_data, ggplot2::aes(x = estimate, y = label)) +
    ggplot2::geom_vline(xintercept = 0, color = "grey65", linetype = "dashed") +
    ggplot2::geom_errorbar(ggplot2::aes(xmin = lower, xmax = upper), width = 0.12, orientation = "y") +
    ggplot2::geom_point(size = 2.8, color = "#156082") +
    ggplot2::labs(
      x = "Matched change in annual citations (95% interval)", y = NULL,
      title = "Citation response after a replication report",
      subtitle = "Three-year window; incomplete collection and limited matching support"
    ) +
    ggplot2::theme_minimal(base_size = 11) +
    ggplot2::theme(panel.grid.minor = ggplot2::element_blank(), panel.grid.major.y = ggplot2::element_blank())
  ggplot2::ggsave(file.path(figure_dir, "replication_estimates.png"), figure, width = 8, height = 3.2, dpi = 160)
}
