estimate_response <- function(changes) {
  stopifnot(!anyDuplicated(changes[c("case_id", "paper_id")]))
  cases <- split(changes, changes$case_id)
  direct <- vapply(cases, function(x) {
    stopifnot(sum(x$target) == 1L, length(unique(x$outcome)) == 1L)
    stopifnot(abs(sum(x$weight[x$target == 0]) - 1) < 1e-8)
    stopifnot(x$weight[x$target == 1] == 1)
    x$change[x$target == 1] - sum(x$change[x$target == 0] * x$weight[x$target == 0])
  }, numeric(1))
  group <- vapply(cases, function(x) x$outcome[1], character(1))
  changes$exposed_success <- changes$target * (changes$outcome == "successful")
  changes$exposed_failed <- changes$target * (changes$outcome == "failed")
  model <- fixest::feols(
    change ~ exposed_success + exposed_failed | case_id,
    data = changes, weights = ~weight, vcov = "iid", notes = FALSE
  )
  coefficients <- c("exposed_success", "exposed_failed")
  estimates <- unname(stats::coef(model)[coefficients])
  expected <- c(mean(direct[group == "successful"]), mean(direct[group == "failed"]))
  if (any(!is.finite(estimates)) || max(abs(estimates - expected)) > 1e-7) {
    stop("Model does not reproduce equal-original contrasts for both groups")
  }
  reports <- length(unique(changes$report_cluster))
  papers <- length(unique(changes$paper_id))
  variance <- matrix(NA_real_, 2, 2)
  inference <- "unavailable: fewer than two clusters"
  if (min(reports, papers) > 1L) {
    variance <- stats::vcov(
      model,
      vcov = ~ paper_id + report_cluster, vcov_fix = FALSE,
      ssc = fixest::ssc(
        K.adj = TRUE, K.fixef = "nonnested", G.adj = TRUE,
        G.df = "min", t.df = "min"
      )
    )[coefficients, coefficients]
    inference <- "two-way paper/report clusters; conditional on matches and labels"
    if (
      any(!is.finite(variance)) ||
        min(eigen(variance, symmetric = TRUE, only.values = TRUE)$values) < -1e-10
    ) {
      variance[, ] <- NA_real_
      inference <- "unavailable: non-positive-semidefinite cluster covariance"
    }
  }
  contrasts <- list(successful = c(1, 0), failed = c(0, 1), failed_minus_successful = c(-1, 1))
  do.call(rbind, lapply(names(contrasts), function(label) {
    weights <- contrasts[[label]]
    estimate <- sum(weights * estimates)
    se <- sqrt(drop(t(weights) %*% variance %*% weights))
    critical <- stats::qt(0.975, min(reports, papers) - 1)
    data.frame(
      outcome = label, estimate = estimate, standard_error = se,
      lower = estimate - critical * se, upper = estimate + critical * se,
      originals = if (label == "failed_minus_successful") length(cases) else sum(group == label),
      report_clusters = reports, physical_papers = papers, inference = inference
    )
  }))
}

estimate_study <- function(matched) {
  estimates <- list()
  dependence <- list()
  for (window in unique(matched$changes$window)) {
    panel <- matched$changes[matched$changes$window == window, ]
    targets <- panel[panel$target == 1, ]
    sizes <- sort(table(targets$report_cluster), decreasing = TRUE)
    largest <- names(sizes)[1]
    supported <- matched$cases$article_id[matched$cases$window == window & !matched$cases$is_outside_support]
    specifications <- list(
      all_eligible = panel,
      omit_largest_report = panel[panel$report_cluster != largest, ],
      no_later_assessment = panel[!panel$has_later_assessment, ],
      no_prior_other_assessment = panel[!panel$has_prior_assessment, ],
      within_donor_pool_range = panel[panel$article_id %in% supported, ]
    )
    for (specification in names(specifications)) {
      selected <- specifications[[specification]]
      if (!all(c("successful", "failed") %in% selected$outcome)) next
      estimates[[length(estimates) + 1L]] <- estimate_response(selected) |>
        dplyr::mutate(window = window, specification = specification)
    }
    donors <- panel[panel$target == 0, ]
    dependence[[window]] <- tibble::tibble(
      window,
      originals = nrow(targets), report_clusters = length(sizes), largest_report = largest,
      largest_report_originals = as.integer(sizes[1]), largest_report_share = as.integer(sizes[1]) / nrow(targets),
      distinct_controls = length(unique(donors$paper_id)), maximum_control_reuse = max(table(donors$paper_id))
    )
  }
  descriptive <- matched$cases |>
    dplyr::group_by(window, outcome) |>
    dplyr::summarise(
      originals = dplyr::n(), reports = dplyr::n_distinct(report_cluster),
      mean_change = mean(difference_in_changes), median_change = median(difference_in_changes),
      mean_target_pre = mean(target_pre), mean_target_post = mean(target_post),
      mean_control_pre = mean(control_pre), mean_control_post = mean(control_post),
      outside_support = sum(is_outside_support),
      placebo_originals = sum(!is.na(placebo_change)), mean_placebo_change = mean(placebo_change, na.rm = TRUE),
      .groups = "drop"
    )
  list(estimates = dplyr::bind_rows(estimates), dependence = dplyr::bind_rows(dependence), descriptive = descriptive)
}
