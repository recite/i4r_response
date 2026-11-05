collect_source_files <- function() {
  receipts <- read_source(file.path(source_dir, "source_snapshots.csv"))
  values <- list()
  for (i in seq_len(nrow(receipts))) {
    receipt <- receipts[i, ]
    relative <- strsplit(receipt$url, paste0("/blob/", receipt$revision, "/"), fixed = TRUE)[[1]][2]
    endpoint <- paste0("repos/", receipt$repository, "/contents/", relative, "?ref=", receipt$revision)
    path <- file.path(cache_dir, "sources", paste0(receipt$source, ".csv"))
    dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
    status <- system2("gh",
      c("api", "-H", shQuote("Accept: application/vnd.github.raw+json"), shQuote(endpoint)),
      stdout = path
    )
    if (status != 0 || digest::digest(file = path, algo = "sha256") != receipt$sha256) {
      stop("Pinned source checksum mismatch")
    }
    values[[receipt$source]] <- read_source(path)
  }
  columns <- names(read_source(file.path(source_dir, "flora_candidates.csv")))
  computed <- c("year_screen", "original_in_i4r", "doi_pair_available", "date_review_required", "registry_record")
  flora <- values$flora[setdiff(columns, computed)]
  original_year <- parse_year(flora$year_o)
  report_year <- parse_year(flora$year_r)
  flora$year_screen <- vapply(seq_len(nrow(flora)), function(i) {
    if (is.na(original_year[i]) || is.na(report_year[i])) {
      return("year_missing_or_invalid")
    }
    reasons <- c(
      if (original_year[i] >= report_year[i] - 2) "insufficient_full_baseline_age",
      if (report_year[i] + 1 > last_citation_year) "insufficient_complete_followup_years"
    )
    if (length(reasons)) paste(reasons, collapse = ";") else "passes_year_screen_only"
  }, character(1))
  originals <- read_source(file.path(i4r_dir, "articles.csv"))
  flora$original_in_i4r <- normalize_doi(flora$doi_o) %in% originals$doi[nzchar(originals$doi)]
  flora$doi_pair_available <- nzchar(normalize_doi(flora$doi_o)) & nzchar(normalize_doi(flora$doi_r))
  flora$date_review_required <- TRUE
  flora$registry_record <- grepl("registr", flora$journal_r, ignore.case = TRUE)
  check_keys(flora, "id")
  write_table(flora, file.path(source_dir, "flora_candidates.csv"))
  units <- read_source(file.path(i4r_dir, "assessment_inventory.csv"))
  links <- read_source(file.path(i4r_dir, "assessment_sources.csv")) |>
    dplyr::filter(relation == "assessment_source") |>
    dplyr::left_join(dplyr::select(units, unit_id, article_id), by = "unit_id", relationship = "many-to-one")
  coding <- values$prior_i4r
  coding <- coding[!coding$url %in% c("", "Mean"), ]
  report_id <- stringr::str_match(coding$url, "/([0-9]+)\\.html$")[, 2]
  if (anyNA(report_id)) stop("Unexpected prior-coding URL")
  prior <- tibble::tibble(
    source_id = sprintf("dp_%03d", as.integer(report_id)), source_url = coding$url,
    computational_score = coding[["narrow replication"]], robustness_score = coding$robust,
    materials_score = coding[["complete materials for replication"]]
  )
  prior$linked_originals <- vapply(prior$source_id, function(id) {
    paste(sort(unique(links$article_id[links$source_id == id]), method = "radix"), collapse = ";")
  }, character(1))
  prior$linked_original_count <- vapply(strsplit(prior$linked_originals, ";", fixed = TRUE), length, integer(1))
  prior$mapping_status <- ifelse(prior$linked_original_count == 1, "one_original",
    ifelse(prior$linked_original_count > 1, "multiple_originals_review_required", "no_assessment_link")
  )
  check_keys(prior, "source_id")
  write_table(prior, file.path(source_dir, "prior_i4r_labels.csv"))
}
