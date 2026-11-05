make_history <- function(annual) {
  check_keys(annual, c("article_id", "year"))
  annual <- annual[annual$status == "complete", ]
  lapply(split(annual, annual$article_id), function(rows) {
    setNames(as.numeric(rows$citations), rows$year)
  })
}

history_matrix <- function(ids, years, histories, missing_reason) {
  result <- t(vapply(ids, function(id) {
    values <- histories[[id]]
    if (!all(as.character(years) %in% names(values))) stop(missing_reason)
    unname(values[as.character(years)])
  }, numeric(length(years))))
  rownames(result) <- ids
  result
}

rank_controls <- function(target, donors, histories, years, limit = 5L) {
  donors <- sort(unique(donors), method = "radix")
  values <- log1p(history_matrix(c(target, donors), years, histories, "incomplete_baseline_histories"))
  controls <- values[-1, , drop = FALSE]
  scale <- sqrt(colMeans(sweep(controls, 2, colMeans(controls))^2))
  active <- scale > 0
  distances <- if (any(active)) {
    rowMeans(sweep(sweep(controls[, active, drop = FALSE], 2, values[1, active]), 2, scale[active], FUN = "/")^2)
  } else {
    rep(0, length(donors))
  }
  tibble::tibble(control_id = donors, distance = unname(round(distances, 10))) |>
    dplyr::arrange(distance, control_id, .locale = "C") |>
    utils::head(limit)
}

compute_contrast <- function(target, donors, histories, pre, post) {
  values <- history_matrix(c(target, donors), c(pre, post), histories, "incomplete_selected_followup")
  target_pre <- mean(values[1, seq_along(pre)])
  target_post <- mean(values[1, length(pre) + seq_along(post)])
  control_pre <- mean(values[-1, seq_along(pre), drop = FALSE])
  control_post <- mean(values[-1, length(pre) + seq_along(post), drop = FALSE])
  tibble::tibble(
    target_pre, target_post, control_pre, control_post,
    difference_in_changes = target_post - target_pre - control_post + control_pre
  )
}

published_before <- function(controls, year) {
  nzchar(controls$publication_date_source) & nzchar(controls$publication_date) &
    suppressWarnings(as.integer(substr(controls$publication_date, 1, 4))) < year
}

match_events <- function(events, inputs, windows = analysis_windows, contrast_before = 3L) {
  events <- events[events$status == "candidate_for_matching", ]
  histories <- make_history(inputs$citations)
  candidates <- inputs$comparison_articles
  pools <- inputs$comparison_pools
  members <- split(inputs$comparison_members$article_id, inputs$comparison_members$pool_id)
  clusters <- connect_reports(events)
  pieces <- list()
  eligibility <- list()
  pool_keys <- paste(pools$journal_id, pools$year, pools$type, sep = "|")
  for (i in seq_len(nrow(events))) {
    event <- events[i, ]
    target <- event$article_id
    year <- event$event_year
    pool_index <- match(paste(event$journal_id, event$indexed_year, event$type, sep = "|"), pool_keys)
    pool <- pools[pool_index, ]
    pool_id <- if (is.na(pool_index)) "" else pool$event_id
    for (window in names(windows)) {
      span <- windows[[window]]
      pre <- seq.int(year - span["before"], year - 1L)
      post <- seq.int(year + 1L, year + span["after"])
      contrast_pre <- if (is.null(contrast_before)) pre else tail(pre, min(length(pre), contrast_before))
      key <- tibble::tibble(article_id = target, window = window, outcome = event$outcome, event_year = year)
      reasons <- character()
      if (max(post) > last_citation_year) reasons <- c(reasons, "insufficient_complete_followup_years")
      if (as.integer(substr(event$original_publisher_date, 1, 4)) >= min(pre)) {
        reasons <- c(reasons, "insufficient_full_baseline_age")
      }
      if (is.na(pool_index) || pool$status != "complete") reasons <- c(reasons, "comparison_sample_unavailable")
      ids <- unique(members[[pool_id]])
      donor_rows <- candidates[match(ids, candidates$article_id), ]
      allowed <- !ids %in% inputs$comparison_exclusions$article_id & published_before(donor_rows, min(pre))
      donors <- ids[allowed %in% TRUE]
      if (!length(donors)) reasons <- c(reasons, "no_eligible_controls")
      selected <- NULL
      if (!length(reasons)) {
        result <- tryCatch(
          {
            selected <- rank_controls(target, donors, histories, pre)
            compute_contrast(target, selected$control_id, histories, contrast_pre, post)
          },
          error = function(error) error
        )
        if (inherits(result, "error")) reasons <- c(reasons, conditionMessage(result))
      }
      eligibility[[length(eligibility) + 1L]] <- dplyr::bind_cols(key, tibble::tibble(
        pool_id,
        eligible_controls = length(donors),
        status = if (length(reasons)) paste(reasons, collapse = ";") else "contrast_available"
      ))
      if (length(reasons)) next
      controls <- selected$control_id
      ids <- c(target, controls)
      is_target <- ids == target
      flags <- tibble::tibble(
        report_cluster = unname(clusters[target]),
        has_later_assessment = !is.na(event$later_assessment_year) && event$later_assessment_year <= max(post),
        has_prior_assessment = event$has_earlier_reproduction || event$has_i4r_overlap
      )
      baseline <- history_matrix(c(target, donors), pre, histories, "incomplete_baseline_histories")
      outside <- any(
        baseline[1, ] < apply(baseline[-1, , drop = FALSE], 2, min) |
          baseline[1, ] > apply(baseline[-1, , drop = FALSE], 2, max)
      )
      holdout <- min(pre) - c(2L, 1L)
      old_enough <- as.integer(substr(event$original_publisher_date, 1, 4)) < min(holdout) &&
        all(published_before(candidates[match(controls, candidates$article_id), ], min(holdout)))
      placebo <- if (old_enough) {
        tryCatch(
          compute_contrast(target, controls, histories, holdout[1], holdout[2])$difference_in_changes,
          error = function(error) NA_real_
        )
      } else {
        NA_real_
      }
      values <- history_matrix(ids, c(pre, post), histories, "incomplete_selected_followup")
      paths <- tibble::tibble(
        event_time = c(pre, post) - year, target_citations = values[1, ],
        control_citations = colMeans(values[-1, , drop = FALSE])
      )
      pieces[[length(pieces) + 1L]] <- list(
        cases = dplyr::bind_cols(key, flags, tibble::tibble(
          title = event$title, reports = event$reports, controls = length(controls),
          is_outside_support = outside, placebo_change = placebo
        ), result),
        matches = dplyr::bind_cols(key[rep(1, length(controls)), ], selected) |>
          dplyr::mutate(weight = 1 / length(controls), pool_id = pool_id),
        changes = dplyr::bind_cols(key[rep(1, length(ids)), ], flags[rep(1, length(ids)), ], tibble::tibble(
          case_id = paste(window, target, sep = "_"), paper_id = ids, target = as.integer(is_target),
          weight = ifelse(is_target, 1, 1 / length(controls)),
          change = rowMeans(values[, length(pre) + seq_along(post), drop = FALSE]) -
            rowMeans(values[, match(contrast_pre, pre), drop = FALSE])
        )),
        paths = dplyr::bind_cols(key[rep(1, nrow(paths)), ], paths),
        balance = dplyr::bind_cols(key[rep(1, length(pre)), ], tibble::tibble(
          year = pre, target_citations = values[1, seq_along(pre)],
          control_citations = colMeans(values[-1, seq_along(pre), drop = FALSE]),
          log_gap = log1p(values[1, seq_along(pre)]) - colMeans(log1p(values[-1, seq_along(pre), drop = FALSE]))
        ))
      )
    }
  }
  if (!length(pieces)) stop("No complete comparisons; no estimates generated")
  result <- setNames(lapply(c("cases", "matches", "changes", "paths", "balance"), function(name) {
    purrr::map_dfr(pieces, name)
  }), c("cases", "matches", "changes", "paths", "balance"))
  result$eligibility <- dplyr::bind_rows(eligibility)
  result
}
