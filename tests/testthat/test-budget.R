testthat::test_that("a process interruption cannot reset a cumulative spending cap", {
  path <- tempfile(fileext = ".json")
  on.exit(unlink(path), add = TRUE)
  balance <- 1
  account <- function() list(prepaid_remaining_usd = balance, daily_remaining_usd = 0, daily_used_usd = 1)
  budget <- start_budget(path, max_paid_usd = 0.0004, account = account)
  reserve_request(budget)
  balance <- balance - 0.0001
  restarted <- start_budget(path, max_paid_usd = 0.0004, account = account)
  testthat::expect_error(reserve_request(restarted), "budget_stop")
  testthat::expect_equal(jsonlite::read_json(path)$unreconciled_paid_reservations, 0.0004)
  for (cap in c(-1, Inf, NaN)) testthat::expect_error(start_budget(path, cap, account), "finite and nonnegative")
})

testthat::test_that("failed final accounting retains the reserved amount", {
  path <- tempfile(fileext = ".json")
  on.exit(unlink(path), add = TRUE)
  unavailable <- FALSE
  account <- function() {
    if (unavailable) stop("account unavailable")
    list(prepaid_remaining_usd = 1, daily_remaining_usd = 0, daily_used_usd = 1)
  }
  budget <- start_budget(path, 0.0004, account)
  reserve_request(budget)
  unavailable <- TRUE
  testthat::expect_error(settle_budget(budget), "account unavailable")
  testthat::expect_equal(jsonlite::read_json(path)$pending_paid_reservation, 0.0004)
})
