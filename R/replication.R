replication_boolean <- function(x) {
  if (!all(x %in% c("True", "False"))) stop("Unexpected exported boolean value")
  x == "True"
}

replication_fit <- function(changes) {
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
  names <- c("exposed_success", "exposed_failed")
  estimates <- unname(stats::coef(model)[names])
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
      model, vcov = ~ paper_id + report_cluster, vcov_fix = FALSE,
      ssc = fixest::ssc(
        K.adj = TRUE, K.fixef = "nonnested", G.adj = TRUE,
        G.df = "min", t.df = "min"
      )
    )[names, names]
    inference <- "two-way paper/report clusters; conditional on matches and labels"
    if (any(!is.finite(variance)) ||
          min(eigen(variance, symmetric = TRUE, only.values = TRUE)$values) < -1e-10) {
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
