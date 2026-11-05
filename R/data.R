read_source <- function(path) {
  readr::read_csv(path,
    col_types = readr::cols(.default = readr::col_character()),
    na = character(), show_col_types = FALSE, progress = FALSE
  )
}

write_table <- function(x, path) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  readr::write_csv(x, path, na = "")
  invisible(x)
}

check_keys <- function(x, columns) {
  if (anyNA(x[columns]) || anyDuplicated(x[columns])) {
    stop("Missing or duplicate keys: ", paste(columns, collapse = ", "))
  }
  invisible(x)
}

normalize_doi <- function(x) {
  x <- stringr::str_to_lower(stringr::str_trim(x))
  x <- stringr::str_remove(x, "^https?://(dx\\.)?doi\\.org/")
  x <- stringr::str_remove(x, "^doi:\\s*")
  ifelse(stringr::str_detect(x, "^10\\.[0-9]{4,9}/\\S+$"), x, "")
}

make_paper_id <- function(doi) {
  paste0("paper_", substr(vapply(doi, digest::digest, character(1), algo = "sha256", serialize = FALSE), 1, 16))
}

normalize_title <- function(x) {
  x <- vapply(x, function(value) {
    if (!nzchar(value)) {
      return("")
    }
    value <- gsub("<", "&lt;", value, fixed = TRUE)
    value <- gsub(">", "&gt;", value, fixed = TRUE)
    xml2::xml_text(xml2::read_html(paste0("<p>", value, "</p>")))
  }, character(1), USE.NAMES = FALSE)
  x <- stringr::str_remove(x, stringr::regex("^RETRACTED(?: ARTICLE)?\\s*:\\s*", ignore_case = TRUE))
  x <- stringr::str_remove(x, "\\s*\\(Team [0-9]+\\)\\s*$")
  x <- stringr::str_remove_all(x, "</?(?:i|b|sup|sub|em|strong)[^>]*>")
  x <- iconv(stringi::stri_trans_nfkd(x), to = "ASCII", sub = "")
  stringr::str_remove_all(tolower(x), "[^a-z0-9]")
}

same_title <- function(x, y) {
  nzchar(x) & nzchar(y) & normalize_title(x) == normalize_title(y)
}

parse_year <- function(x) {
  result <- rep(NA_integer_, length(x))
  valid <- stringr::str_detect(x, "^[12][0-9]{3}$")
  result[valid] <- as.integer(x[valid])
  result
}

parse_flag <- function(x) {
  if (is.logical(x)) {
    return(x)
  }
  if (!all(x %in% c("True", "False", "TRUE", "FALSE"))) stop("Unknown boolean value")
  tolower(x) == "true"
}

validate_histories <- function(annual, receipts, last_year = last_citation_year) {
  check_keys(annual, c("article_id", "year"))
  check_keys(receipts, "article_id")
  if (!all(annual$article_id %in% receipts$article_id)) stop("History without receipt")
  annual$year <- as.integer(annual$year)
  annual$citations <- as.numeric(annual$citations)
  if (anyNA(annual[c("year", "citations")]) || any(annual$citations < 0 | annual$citations %% 1 != 0)) {
    stop("Invalid annual counts")
  }
  groups <- split(annual, annual$article_id)
  for (i in seq_len(nrow(receipts))) {
    receipt <- receipts[i, ]
    rows <- groups[[receipt$article_id]]
    if (receipt$status != "complete") {
      if (nrow(rows) %||% 0L > 0) stop("Unavailable history has observations")
      next
    }
    first <- as.integer(receipt$panel_first_year)
    expected <- if (first > last_year) integer() else seq.int(first, last_year)
    if (!setequal(rows$year, expected)) stop("Annual history has missing or extra years")
    if (!all(rows$status == "complete")) stop("Incomplete annual observation")
    if (
      sum(rows$citations) != as.numeric(receipt$api_count) ||
        sum(rows$citations) != as.numeric(receipt$sum_counts)
    ) {
      stop("Annual history does not reconcile")
    }
    before <- sum(rows$citations[rows$year < as.integer(receipt$indexed_publication_year)])
    if (before != as.numeric(receipt$before_publication)) stop("Pre-publication counts do not reconcile")
  }
  invisible(TRUE)
}

`%||%` <- function(x, y) if (is.null(x) || length(x) == 0L) y else x

read_study_inputs <- function() {
  names <- c(
    "flora_candidates", "metadata", "comparison_articles", "comparison_pools",
    "comparison_members", "comparison_exclusions", "citations", "citation_totals"
  )
  inputs <- setNames(lapply(names, function(name) read_source(file.path(source_dir, paste0(name, ".csv")))), names)
  check_keys(inputs$flora_candidates, "id")
  check_keys(inputs$metadata, "doi")
  check_keys(inputs$comparison_articles, "article_id")
  check_keys(inputs$comparison_pools, "event_id")
  check_keys(inputs$comparison_members, c("pool_id", "article_id", "openalex_id"))
  if (
    !all(inputs$comparison_members$article_id %in% inputs$comparison_articles$article_id) ||
      !all(inputs$comparison_members$pool_id %in% inputs$comparison_pools$event_id)
  ) {
    stop("Unmatched pool member")
  }
  validate_histories(inputs$citations, inputs$citation_totals)
  inputs
}
