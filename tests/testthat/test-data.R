testthat::test_that("missing histories cannot become zero citations or duplicate joined observations", {
  annual <- tibble::tibble(article_id = "a", year = "2025", citations = "0", status = "complete")
  receipt <- tibble::tibble(
    article_id = "a", status = "complete", panel_first_year = "2025",
    indexed_publication_year = "2025", api_count = "0", sum_counts = "0", before_publication = "0"
  )
  testthat::expect_true(validate_histories(annual, receipt))
  testthat::expect_error(validate_histories(annual[0, ], receipt), "missing or extra")
  testthat::expect_error(validate_histories(dplyr::bind_rows(annual, annual), receipt), "duplicate")
  receipt$status <- "unavailable"
  testthat::expect_error(validate_histories(annual, receipt), "Unavailable history")
  testthat::expect_error(
    parse_year_counts(list(meta = list(count = 3), group_by = list(list(key = "2020", count = 2)))), "reconcile"
  )
})

testthat::test_that("chronology is selected before outcome filtering", {
  pairs <- tibble::tibble(
    id = c("1", "2"), doi_r = c("10.1234/one", "10.1234/two"),
    year_r = c("2010", "2015"), outcome = c("mixed", "failed")
  )
  metadata <- tibble::tibble(
    doi = pairs$doi_r, publisher_date = c("2010", "2015"),
    publisher_type = "journal-article", publisher_journal = "Journal"
  )
  first <- select_first_report(pairs, metadata)
  testthat::expect_equal(first$event_year, 2010L)
  testthat::expect_equal(first$outcome, "mixed")
  testthat::expect_equal(first$later_assessment_year, 2015L)
  unresolved <- select_first_report(pairs, metadata[2, ])
  testthat::expect_equal(unresolved$chronology_status, "earlier_or_same_year_unverified_report")
  pairs$year_r <- c("2015", "2015")
  metadata$publisher_date <- "2015"
  pairs$outcome <- c("successful", "failed")
  testthat::expect_equal(select_first_report(pairs, metadata)$outcome, "mixed")
})
