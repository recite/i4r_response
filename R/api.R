openalex_key <- function() {
  value <- trimws(Sys.getenv("OPENALEX_API_KEY"))
  if (nzchar(value)) {
    return(value)
  }
  config <- Sys.getenv("XDG_CONFIG_HOME", unset = path.expand("~/.config"))
  path <- file.path(config, "openalex", "api_key")
  if (file.exists(path)) {
    return(trimws(readLines(path, warn = FALSE)[1]))
  }
  stop("Set OPENALEX_API_KEY or provide ~/.config/openalex/api_key")
}

api_request <- function(url) {
  request <- httr2::request(url) |>
    httr2::req_user_agent("i4r-response-research/0.2") |>
    httr2::req_timeout(30) |>
    httr2::req_retry(
      max_tries = 4, retry_on_failure = TRUE,
      is_transient = function(response) httr2::resp_status(response) %in% c(429, 500, 502, 503, 504)
    )
  if (httr2::url_parse(url)$hostname == "api.openalex.org") {
    request <- httr2::req_auth_bearer_token(request, openalex_key())
  }
  request
}

api_url <- function(endpoint, ...) {
  httr2::request(paste0("https://api.openalex.org/", endpoint)) |>
    httr2::req_url_query(..., .space = "form") |>
    purrr::pluck("url")
}

read_account <- function() {
  api_request("https://api.openalex.org/rate-limit") |>
    httr2::req_perform() |>
    httr2::resp_body_json(simplifyVector = FALSE) |>
    purrr::pluck("rate_limit")
}

write_json_atomic <- function(value, path) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  temporary <- tempfile(pattern = ".receipt-", tmpdir = dirname(path))
  on.exit(unlink(temporary), add = TRUE)
  jsonlite::write_json(value, temporary, auto_unbox = TRUE, pretty = TRUE, null = "null", digits = NA)
  if (!file.rename(temporary, path)) stop("Could not commit receipt")
}

start_budget <- function(path, max_paid_usd = 0, account = read_account) {
  if (length(max_paid_usd) != 1L || !is.finite(max_paid_usd) || max_paid_usd < 0) {
    stop("The prepaid cap must be finite and nonnegative")
  }
  previous <- if (file.exists(path)) jsonlite::read_json(path) else list()
  current <- account()
  budget <- new.env(parent = emptyenv())
  budget$path <- path
  budget$account <- account
  budget$limit <- max_paid_usd
  budget$initial_balance <- current$prepaid_remaining_usd
  budget$initial_daily_used <- current$daily_used_usd
  budget$prior_paid <- previous$provider_reported_prepaid_debit %||% 0
  budget$unreconciled <- (previous$unreconciled_paid_reservations %||% 0) +
    (previous$pending_paid_reservation %||% 0)
  budget$paid <- budget$prior_paid
  budget$free <- current$daily_remaining_usd
  budget$pending <- 0
  budget$requests <- 0L
  budget$daily_used <- current$daily_used_usd
  save_budget(budget)
  budget
}

save_budget <- function(budget) {
  write_json_atomic(list(
    allowed_paid_usd = budget$limit, provider_reported_prepaid_debit = budget$paid,
    unreconciled_paid_reservations = budget$unreconciled, pending_paid_reservation = budget$pending,
    daily_usage_increase = budget$daily_used - budget$initial_daily_used,
    qualification = "Account-level changes; interrupted reservations consume the cap and are not verified charges."
  ), budget$path)
}

settle_budget <- function(budget) {
  current <- budget$account()
  budget$paid <- budget$prior_paid + max(0, budget$initial_balance - current$prepaid_remaining_usd)
  budget$free <- current$daily_remaining_usd
  budget$daily_used <- current$daily_used_usd
  budget$pending <- 0
  budget$requests <- 0L
  save_budget(budget)
}

reserve_request <- function(budget, maximum_cost = 0.0004) {
  if (is.null(budget)) stop("OpenAlex list requests require a spending guard")
  if (!is.finite(maximum_cost) || maximum_cost < 0) stop("Invalid request cost")
  if (budget$requests >= 100L) settle_budget(budget)
  paid <- max(0, maximum_cost - budget$free)
  if (budget$paid + budget$unreconciled + budget$pending + paid > budget$limit + 1e-12) {
    stop("budget_stop")
  }
  budget$free <- max(0, budget$free - maximum_cost)
  budget$pending <- budget$pending + paid
  budget$requests <- budget$requests + 1L
  save_budget(budget)
  invisible(TRUE)
}

cached_json <- function(url, folder, fetch = FALSE, budget = NULL) {
  path <- file.path(cache_dir, folder, paste0(digest::digest(url, algo = "sha256", serialize = FALSE), ".json"))
  receipt_path <- paste0(path, ".source.json")
  if (file.exists(path)) {
    if (!file.exists(receipt_path)) stop("Missing cache receipt")
    receipt <- jsonlite::read_json(receipt_path)
    if (!identical(receipt$url, url) || receipt$sha256 != digest::digest(file = path, algo = "sha256")) {
      stop("Cache receipt mismatch")
    }
  } else {
    if (!fetch) stop("response_not_cached")
    if (httr2::url_parse(url)$hostname == "api.openalex.org") reserve_request(budget)
    response <- api_request(url) |> httr2::req_perform()
    bytes <- httr2::resp_body_raw(response)
    jsonlite::fromJSON(rawToChar(bytes), simplifyVector = FALSE)
    dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
    writeBin(bytes, path)
    receipt <- list(
      url = url, retrieved_at = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC"),
      sha256 = digest::digest(bytes, algo = "sha256", serialize = FALSE), bytes = length(bytes)
    )
    write_json_atomic(receipt, receipt_path)
  }
  list(payload = jsonlite::read_json(path), receipt = receipt, path = path)
}

write_metadata_receipts <- function() {
  files <- list.files(cache_dir, pattern = "\\.source\\.json$", recursive = TRUE, full.names = TRUE)
  rows <- purrr::map_dfr(files, function(path) {
    receipt <- jsonlite::read_json(path)
    tibble::tibble(
      source_sha256 = receipt$sha256, source_url = receipt$url, retrieved_at = receipt$retrieved_at,
      bytes = as.character(receipt$bytes), source_path = sub("\\.source\\.json$", "", path)
    )
  })
  old_path <- file.path(source_dir, "metadata_sources.csv")
  old <- if (file.exists(old_path)) read_source(old_path) else rows[0, ]
  rows$source_path <- sub(paste0(project_root, "/"), "", rows$source_path, fixed = TRUE)
  write_table(dplyr::bind_rows(old, rows) |> dplyr::distinct(), old_path)
}
