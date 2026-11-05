source(file.path("..", "..", "R", "replication.R"))

testthat::test_that("weighted model preserves equal-original effects with unequal donor counts", {
  rows <- lapply(seq_len(12), function(i) {
    k <- 1L + i %% 3L
    data.frame(
      case_id = paste0("case", i),
      paper_id = c(paste0("target", i), paste0("donor", seq_len(k))),
      report_cluster = paste0("report", ceiling(i / 2)),
      outcome = if (i <= 6) "successful" else "failed",
      target = c(1, rep(0, k)), weight = c(1, rep(1 / k, k)),
      change = c(i, rep(2, k))
    )
  })
  result <- replication_fit(do.call(rbind, rows))
  testthat::expect_equal(result$estimate[result$outcome == "successful"], 1.5)
  testthat::expect_equal(result$estimate[result$outcome == "failed"], 7.5)
  testthat::expect_equal(result$estimate[result$outcome == "failed_minus_successful"], 6)
  testthat::expect_equal(unique(result$report_clusters), 6L)
  testthat::expect_equal(unique(result$physical_papers), 15L)
  bad <- do.call(rbind, rows)
  bad$weight[bad$target == 0] <- 1
  testthat::expect_error(replication_fit(bad))
})

testthat::test_that("Python boolean exports are parsed explicitly", {
  exported <- read.csv(text = "flag\nTrue\nFalse\n", stringsAsFactors = FALSE)
  testthat::expect_identical(replication_boolean(exported$flag), c(TRUE, FALSE))
  testthat::expect_error(replication_boolean(c("True", "unknown")))
})
