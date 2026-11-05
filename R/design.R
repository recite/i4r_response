assess_design <- function(prepared) {
  windows <- list(
    three = c(before = 3L, after = 3L), five = c(before = 5L, after = 3L),
    eight = c(before = 8L, after = 3L), ten = c(before = 10L, after = 3L)
  )
  matched <- match_events(prepared$registry$events, prepared$inputs, windows, contrast_before = 3L)
  common <- Reduce(intersect, lapply(names(windows), function(window) {
    matched$cases$article_id[matched$cases$window == window]
  }))
  estimates <- list()
  for (window in names(windows)) {
    panel <- matched$changes[matched$changes$window == window, ]
    for (sample in c("available", "common")) {
      selected <- if (sample == "common") panel[panel$article_id %in% common, ] else panel
      estimates[[length(estimates) + 1L]] <- estimate_response(selected) |>
        dplyr::mutate(matching_years = windows[[window]]["before"], sample = sample)
    }
  }
  coverage <- matched$eligibility |>
    dplyr::group_by(window) |>
    dplyr::summarise(
      roster = dplyr::n(),
      old_enough = sum(!grepl("insufficient_full_baseline_age", status)),
      available = sum(status == "contrast_available"),
      baseline_uncollected = sum(status == "incomplete_baseline_histories"), .groups = "drop"
    ) |>
    dplyr::mutate(matching_years = vapply(window, function(x) windows[[x]]["before"], numeric(1))) |>
    dplyr::arrange(matching_years)
  histories <- make_history(prepared$inputs$citations)
  members <- split(prepared$inputs$comparison_members$article_id, prepared$inputs$comparison_members$pool_id)
  candidates <- prepared$inputs$comparison_articles
  validation <- list()
  for (i in seq_len(nrow(matched$cases))) {
    case <- matched$cases[i, ]
    span <- windows[[case$window]]["before"]
    if (span < 5) next
    selected_pool <- matched$eligibility$pool_id[
      matched$eligibility$article_id == case$article_id & matched$eligibility$window == case$window
    ]
    ids <- members[[selected_pool]]
    rows <- candidates[match(ids, candidates$article_id), ]
    allowed <- !ids %in% prepared$inputs$comparison_exclusions$article_id &
      published_before(rows, case$event_year - span)
    donors <- ids[allowed %in% TRUE]
    training <- seq.int(case$event_year - span, case$event_year - 3L)
    controls <- rank_controls(case$article_id, donors, histories, training)$control_id
    values <- compute_contrast(
      case$article_id, controls, histories, case$event_year - 2L, case$event_year - 1L
    )
    validation[[length(validation) + 1L]] <- tibble::tibble(
      article_id = case$article_id, outcome = case$outcome, matching_years = span,
      validation_change = values$difference_in_changes,
      validation_gap = mean(c(values$target_pre - values$control_pre, values$target_post - values$control_post))
    )
  }
  list(
    coverage = coverage, estimates = dplyr::bind_rows(estimates),
    validation = dplyr::bind_rows(validation), cases = matched$cases,
    matches = matched$matches, common_originals = common
  )
}

write_design_exhibits <- function(design) {
  rows <- c(
    "\\begin{tabular}{lrrrr}", "\\toprule",
    "Matching years & Old enough & Available & Common sample & Missing baseline \\\\", "\\midrule"
  )
  for (i in seq_len(nrow(design$coverage))) {
    row <- design$coverage[i, ]
    rows <- c(rows, sprintf(
      "%s & %s & %s & %s & %s \\\\", row$matching_years, row$old_enough, row$available,
      length(design$common_originals), row$baseline_uncollected
    ))
  }
  writeLines(c(rows, "\\bottomrule", "\\end{tabular}"), file.path(table_dir, "design_coverage.tex"))
  estimates <- design$estimates |>
    dplyr::filter(outcome == "failed_minus_successful") |>
    dplyr::mutate(
      matching_years = factor(matching_years, levels = c(10, 8, 5, 3), labels = c("Ten", "Eight", "Five", "Three")),
      sample = factor(sample,
        levels = c("available", "common"), labels = c("Available papers", "Same papers at every length")
      )
    )
  figure <- ggplot2::ggplot(estimates, ggplot2::aes(x = estimate, y = matching_years)) +
    ggplot2::geom_vline(xintercept = 0, linetype = "dashed", color = "grey60", linewidth = 0.35) +
    ggplot2::geom_errorbar(ggplot2::aes(xmin = lower, xmax = upper), orientation = "y", width = 0.1) +
    ggplot2::geom_point(color = "#156082", size = 2.4) +
    ggplot2::facet_wrap(~sample, nrow = 1) +
    ggplot2::labs(x = "Failed minus successful (citations per paper per year)", y = "Years used for matching") +
    study_theme() +
    ggplot2::theme(panel.grid.major.y = ggplot2::element_blank())
  ggplot2::ggsave(file.path(figure_dir, "matching_history.pdf"), figure, width = 6.5, height = 2.5)
  validation <- design$validation |>
    dplyr::group_by(matching_years, outcome) |>
    dplyr::summarise(
      originals = dplyr::n(), mean_gap = mean(validation_gap), mean_change = mean(validation_change), .groups = "drop"
    )
  write_table(validation, file.path(table_dir, "design_validation_summary.csv"))
  rows <- c(
    "\\begin{tabular}{llrrr}", "\\toprule",
    "History & Outcome & Originals & Level gap & Change gap \\\\", "\\midrule"
  )
  for (i in seq_len(nrow(validation))) {
    row <- validation[i, ]
    rows <- c(rows, sprintf(
      "%s years & %s & %s & $%+.2f$ & $%+.2f$ \\\\", row$matching_years,
      if (row$outcome == "successful") "Successful" else "Failed", row$originals, row$mean_gap, row$mean_change
    ))
  }
  writeLines(c(rows, "\\bottomrule", "\\end{tabular}"), file.path(table_dir, "design_validation.tex"))
}
