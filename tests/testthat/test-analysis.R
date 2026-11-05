testthat::test_that("the complete data reproduce the independently checked matched contrasts", {
  matched <- readRDS(file.path(derived_dir, "matched_data.rds"))
  results <- readRDS(file.path(derived_dir, "results.rds"))
  main <- results$estimates |>
    dplyr::filter(specification == "all_eligible", window == "three_year")
  testthat::expect_equal(main$originals, c(138L, 144L, 282L))
  testthat::expect_equal(main$estimate, c(2.994685990338, 3.280555555556, 0.285869565218), tolerance = 1e-8)
  annual <- read_source(file.path(source_dir, "citations.csv"))
  annual$citations <- as.numeric(annual$citations)
  annual$year <- as.integer(annual$year)
  case <- matched$cases[matched$cases$window == "three_year", ][1, ]
  donors <- matched$matches |>
    dplyr::filter(article_id == case$article_id, window == "three_year")
  selected <- annual |>
    dplyr::filter(
      article_id %in% c(case$article_id, donors$control_id),
      year %in% c(seq(case$event_year - 3, case$event_year - 1), seq(case$event_year + 1, case$event_year + 3))
    ) |>
    dplyr::mutate(period = ifelse(year < case$event_year, "pre", "post")) |>
    dplyr::group_by(article_id, period) |>
    dplyr::summarise(citations = mean(citations), .groups = "drop") |>
    tidyr::pivot_wider(names_from = period, values_from = citations) |>
    dplyr::mutate(change = post - pre)
  direct <- selected$change[selected$article_id == case$article_id] -
    mean(selected$change[selected$article_id != case$article_id])
  testthat::expect_equal(direct, case$difference_in_changes, tolerance = 1e-10)
  testthat::expect_equal(sum(matched$cases$window == "short"), 365L)
})

testthat::test_that("equal-original weighting survives unequal numbers of reused controls", {
  rows <- lapply(seq_len(12), function(i) {
    controls <- 1L + i %% 3L
    tibble::tibble(
      case_id = paste0("case", i), paper_id = c(paste0("target", i), paste0("donor", seq_len(controls))),
      report_cluster = paste0("report", ceiling(i / 2)), outcome = if (i <= 6) "successful" else "failed",
      target = c(1L, rep(0L, controls)), weight = c(1, rep(1 / controls, controls)),
      change = c(i, rep(2, controls))
    )
  })
  result <- estimate_response(dplyr::bind_rows(rows))
  testthat::expect_equal(result$estimate, c(1.5, 7.5, 6), tolerance = 1e-10)
  testthat::expect_equal(unique(result$physical_papers), 15L)
  testthat::expect_equal(unique(result$report_clusters), 6L)
})

testthat::test_that("matching uses standardised baseline distances and never replaces missing follow-up", {
  histories <- list(
    target = c(`1` = 10, `2` = 14, `3` = 20),
    b = c(`1` = 8, `2` = 12, `3` = 13), c = c(`1` = 4, `2` = 8, `3` = 11)
  )
  matches <- rank_controls("target", c("c", "b"), histories, 1:2, limit = 1)
  expected <- mean(c(
    ((log(9) - log(11)) / (abs(log(9) - log(5)) / 2))^2,
    ((log(13) - log(15)) / (abs(log(13) - log(9)) / 2))^2
  ))
  testthat::expect_equal(matches$control_id, "b")
  testthat::expect_equal(matches$distance, expected, tolerance = 1e-9)
  histories$b["3"] <- 100000
  testthat::expect_equal(rank_controls("target", c("c", "b"), histories, 1:2, limit = 1), matches)
  histories$b <- histories$b[c("1", "2")]
  testthat::expect_error(
    compute_contrast("target", matches$control_id, histories, 1:2, 3), "incomplete_selected_followup"
  )
})
