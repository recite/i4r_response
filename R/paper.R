write_paper <- function(prepared, matched, results, design) {
  estimates <- results$estimates
  main <- estimates[estimates$specification == "all_eligible", ]
  events <- prepared$registry$events
  eligible <- events[events$status == "candidate_for_matching", ]
  primary <- matched$cases[matched$cases$window == "five_year", ]
  dependence <- results$dependence[results$dependence$window == "five_year", ]
  descriptive <- results$descriptive[results$descriptive$window == "five_year", ]
  macros <- new.env(parent = emptyenv())
  macros$lines <- character()
  add <- function(name, value) {
    macros$lines <- c(macros$lines, sprintf("\\newcommand{\\%s}{%s}", name, value))
  }
  integer_text <- function(x) format(x, big.mark = ",", scientific = FALSE, trim = TRUE)
  number_text <- function(x) sprintf("\\ensuremath{%+.2f}", x)
  interval_text <- function(lower, upper) sprintf("\\ensuremath{[%.2f,\\,%.2f]}", lower, upper)
  add("RosterOriginals", integer_text(nrow(events)))
  add("EligibleOriginals", integer_text(nrow(eligible)))
  add("EligibleSuccessful", sum(eligible$outcome == "successful"))
  add("EligibleFailed", sum(eligible$outcome == "failed"))
  add("OutsideSupport", sum(primary$is_outside_support))
  add("OutsidePercent", sprintf("%.1f", 100 * mean(primary$is_outside_support)))
  add("ReportClusters", dependence$report_clusters)
  add("LargestReport", dependence$largest_report_originals)
  add("DistinctControls", dependence$distinct_controls)
  add("MaximumReuse", dependence$maximum_control_reuse)
  add("StoppedHistories", integer_text(sum(prepared$inputs$citation_totals$detail == "budget_stop")))
  add("CitationsThrough", last_citation_year)
  add("CommonHistoryN", length(design$common_originals))
  labels <- c("Three", "Five", "Eight", "Ten")
  years <- c(3, 5, 8, 10)
  for (i in seq_along(years)) {
    row <- design$coverage[design$coverage$matching_years == years[i], ]
    add(paste0(labels[i], "HistoryN"), row$available)
  }
  add("FirstEventYear", min(primary$event_year))
  add("LastEventYear", max(primary$event_year))
  for (window in c("five_year", "short")) {
    prefix <- if (window == "five_year") "Main" else "Short"
    for (outcome in c("successful", "failed", "failed_minus_successful")) {
      suffix <- switch(outcome,
        successful = "Successful",
        failed = "Failed",
        failed_minus_successful = "Difference"
      )
      row <- main[main$window == window & main$outcome == outcome, ]
      stopifnot(nrow(row) == 1L)
      name <- paste0(prefix, suffix)
      add(paste0(name, "N"), row$originals)
      add(paste0(name, "Estimate"), number_text(row$estimate))
      add(paste0(name, "Interval"), interval_text(row$lower, row$upper))
    }
  }
  for (outcome in c("successful", "failed")) {
    prefix <- if (outcome == "successful") "Successful" else "Failed"
    row <- descriptive[descriptive$outcome == outcome, ]
    add(paste0(prefix, "Pre"), sprintf("%.1f", row$mean_target_pre))
    add(paste0(prefix, "ControlPre"), sprintf("%.1f", row$mean_control_pre))
    add(paste0(prefix, "PlaceboN"), row$placebo_originals)
    add(paste0(prefix, "Placebo"), number_text(row$mean_placebo_change))
  }
  writeLines(macros$lines, file.path(table_dir, "macros.tex"))

  outcome_labels <- c(successful = "Successful", failed = "Failed", failed_minus_successful = "Failed minus successful")
  window_labels <- c(
    five_year = "Five-year matching history", three_year = "Three-year matching history",
    short = "Two before / one after"
  )
  specifications <- c(
    all_eligible = "All completed comparisons", omit_largest_report = "Omit largest report",
    no_later_assessment = "No later assessment", no_prior_other_assessment = "No prior other assessment",
    within_donor_pool_range = "Within candidate range"
  )
  rows <- c("\\toprule", "Window and sample & Originals & Difference & 95\\% interval \\\\", "\\midrule")
  for (window in names(window_labels)) {
    rows <- c(rows, sprintf("\\multicolumn{4}{l}{\\textit{%s}} \\\\", window_labels[[window]]))
    for (specification in names(specifications)) {
      row <- estimates |>
        dplyr::filter(
          .data$window == .env$window,
          .data$specification == .env$specification,
          outcome == "failed_minus_successful"
        )
      rows <- c(rows, sprintf(
        "%s & %s & %s & %s \\\\", specifications[[specification]], row$originals,
        number_text(row$estimate), interval_text(row$lower, row$upper)
      ))
    }
    rows <- c(rows, "\\addlinespace")
  }
  writeLines(
    c("\\begin{tabular}{lrrr}", rows, "\\bottomrule", "\\end{tabular}"),
    file.path(table_dir, "sensitivity.tex")
  )

  rows <- c("\\toprule", "Quantity & Successful & Failed \\\\", "\\midrule")
  success <- descriptive[descriptive$outcome == "successful", ]
  failed <- descriptive[descriptive$outcome == "failed", ]
  fields <- c(
    originals = "Original papers", mean_target_pre = "Original citations before report (per year)",
    mean_target_post = "Original citations after report (per year)",
    mean_control_pre = "Control citations before report (per year)",
    mean_control_post = "Control citations after report (per year)",
    outside_support = "Outside candidate range (papers)",
    placebo_originals = "With held-out pre-period data (papers)",
    mean_placebo_change = "Held-out difference in annual changes"
  )
  for (field in names(fields)) {
    fmt <- if (field %in% c("originals", "outside_support", "placebo_originals")) "%d" else "%.2f"
    rows <- c(rows, sprintf(
      "%s & %s & %s \\\\",
      fields[[field]], sprintf(fmt, success[[field]]), sprintf(fmt, failed[[field]])
    ))
  }
  writeLines(
    c("\\begin{tabular}{lrr}", rows, "\\bottomrule", "\\end{tabular}"),
    file.path(table_dir, "diagnostics.tex")
  )

  plot_data <- main[main$window %in% c("five_year", "three_year"), ] |>
    dplyr::mutate(
      label = factor(outcome, levels = rev(names(outcome_labels)), labels = rev(unname(outcome_labels))),
      window_label = factor(window, levels = names(window_labels), labels = unname(window_labels))
    )
  figure <- ggplot2::ggplot(plot_data, ggplot2::aes(x = estimate, y = label)) +
    ggplot2::geom_vline(xintercept = 0, color = "grey60", linetype = "dashed", linewidth = 0.35) +
    ggplot2::geom_errorbar(ggplot2::aes(xmin = lower, xmax = upper), width = 0.1, orientation = "y") +
    ggplot2::geom_point(size = 2.4, color = "#156082") +
    ggplot2::facet_wrap(~window_label, nrow = 1) +
    ggplot2::labs(x = "Matched change in citations per paper per year", y = NULL) +
    study_theme() +
    ggplot2::theme(panel.grid.major.y = ggplot2::element_blank())
  ggplot2::ggsave(file.path(figure_dir, "citation_response.pdf"), figure, width = 6.5, height = 2.6)

  paths <- matched$paths |>
    dplyr::filter(window == "five_year") |>
    dplyr::group_by(outcome, event_time) |>
    dplyr::summarise(
      Original = mean(target_citations), Controls = mean(control_citations), .groups = "drop"
    ) |>
    tidyr::pivot_longer(c("Original", "Controls"), names_to = "series", values_to = "citations") |>
    dplyr::mutate(
      outcome = factor(outcome, levels = c("successful", "failed"), labels = c("Successful", "Failed")),
      segment = interaction(series, event_time < 0)
    )
  figure <- ggplot2::ggplot(paths, ggplot2::aes(x = event_time, y = citations, color = series, linetype = series)) +
    ggplot2::geom_vline(xintercept = 0, color = "grey70", linewidth = 0.35) +
    ggplot2::geom_line(ggplot2::aes(group = segment), linewidth = 0.6) +
    ggplot2::geom_point(size = 1.5) +
    ggplot2::facet_wrap(~outcome, nrow = 1) +
    ggplot2::scale_color_manual(values = c(Original = "grey15", Controls = "#156082")) +
    ggplot2::scale_linetype_manual(values = c(Original = "solid", Controls = "dashed")) +
    ggplot2::scale_x_continuous(breaks = -5:3) +
    ggplot2::scale_y_continuous(limits = c(0, NA)) +
    ggplot2::labs(
      x = "Years relative to report publication", y = "Citations per paper per year",
      color = NULL, linetype = NULL
    ) +
    study_theme() +
    ggplot2::theme(legend.position = "bottom")
  ggplot2::ggsave(file.path(figure_dir, "citation_paths.pdf"), figure, width = 6.5, height = 2.6)
}
