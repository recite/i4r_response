select_first_report <- function(rows, metadata) {
  report_doi <- normalize_doi(rows$doi_r)
  matched <- match(report_doi, metadata$doi)
  dates <- metadata$publisher_date[matched]
  journals <- metadata$publisher_journal[matched]
  verified <- !is.na(dates) & nzchar(dates) & metadata$publisher_type[matched] == "journal-article" &
    !startsWith(report_doi, "10.2139/") & !stringr::str_detect(tolower(journals), "ssrn")
  verified[is.na(verified)] <- FALSE
  empty <- list(
    event_year = NA_integer_, outcome = "", reports = "", selected_ids = "",
    chronology_status = "no_verified_report_publication", later_assessment_year = NA_integer_
  )
  if (!any(verified)) {
    return(empty)
  }
  years <- suppressWarnings(as.integer(substr(dates, 1, 4)))
  event_year <- min(years[verified])
  selected <- verified & years == event_year
  labels <- unique(rows$outcome[selected])
  source_years <- parse_year(rows$year_r)
  unresolved <- any(!verified & (is.na(source_years) | source_years <= event_year))
  later <- c(years[verified & years > event_year], source_years[!verified & source_years > event_year])
  later <- later[!is.na(later)]
  list(
    event_year = event_year, outcome = if (length(labels) == 1L) labels else "mixed",
    reports = paste(sort(unique(report_doi[selected]), method = "radix"), collapse = ";"),
    selected_ids = paste(sort(rows$id[selected], method = "radix"), collapse = ";"),
    chronology_status = if (unresolved) {
      "earlier_or_same_year_unverified_report"
    } else {
      "earliest_recorded_journal_report_year"
    },
    later_assessment_year = if (length(later)) min(later) else NA_integer_
  )
}

build_events <- function(pairs, metadata) {
  check_keys(metadata, "doi")
  metadata$title_key <- normalize_title(metadata$publisher_title)
  pairs$original_doi <- normalize_doi(pairs$doi_o)
  pairs$report_doi <- normalize_doi(pairs$doi_r)
  pairs$original_title_key <- normalize_title(pairs$title_o)
  pairs$report_title_key <- normalize_title(pairs$title_r)
  originals <- pairs[pairs$type == "replication" & nzchar(pairs$original_doi), ]
  groups <- split(originals, originals$original_doi)
  other <- pairs[pairs$type != "replication" & nzchar(pairs$original_doi), ]
  results <- lapply(sort(names(groups), method = "radix"), function(doi) {
    rows <- groups[[doi]]
    position <- match(doi, metadata$doi)
    meta <- if (is.na(position)) {
      as.list(setNames(rep("", ncol(metadata)), names(metadata)))
    } else {
      as.list(metadata[position, ])
    }
    event <- select_first_report(rows, metadata)
    chosen <- rows$id %in% strsplit(event$selected_ids, ";", fixed = TRUE)[[1]]
    reports <- metadata[match(rows$report_doi, metadata$doi), ]
    agrees <- nzchar(rows$report_title_key) & rows$report_title_key == reports$title_key
    agrees[is.na(agrees)] <- FALSE
    reasons <- character()
    if (meta$openalex_type != "article") reasons <- c(reasons, "original_document_type_review_required")
    if (event$chronology_status != "earliest_recorded_journal_report_year") {
      reasons <- c(reasons, event$chronology_status)
    }
    if (!event$outcome %in% c("successful", "failed")) reasons <- c(reasons, "nonbinary_or_unresolved_outcome")
    if (!nzchar(meta$openalex_id) || meta$publisher_type != "journal-article") {
      reasons <- c(reasons, "original_identity_or_journal_metadata_unavailable")
    }
    if (!nzchar(meta$journal_id) || !nzchar(meta$indexed_year)) reasons <- c(reasons, "original_journal_year_missing")
    if (meta$retracted != "False") reasons <- c(reasons, "original_current_retraction_status_not_clear")
    if (!nzchar(meta$title_key) || !all(rows$original_title_key == meta$title_key)) {
      reasons <- c(reasons, "original_title_review_required")
    }
    if (any(chosen & !agrees)) reasons <- c(reasons, "report_title_review_required")
    if (any(chosen & rows$report_doi == doi)) reasons <- c(reasons, "original_equals_replication")
    earlier <- FALSE
    if (!is.na(event$event_year)) {
      other_years <- parse_year(other$year_r[other$original_doi == doi])
      earlier <- any(is.na(other_years) | other_years <= event$event_year)
      if (!nzchar(meta$publisher_date) || as.integer(substr(meta$publisher_date, 1, 4)) >= event$event_year - 2L) {
        reasons <- c(reasons, "insufficient_full_baseline_age")
      }
      if (event$event_year + 1L > last_citation_year) reasons <- c(reasons, "insufficient_complete_followup_years")
    }
    record <- tibble::as_tibble(c(list(
      article_id = make_paper_id(doi), doi = doi,
      title = if (nzchar(meta$publisher_title)) meta$publisher_title else rows$title_o[1]
    ), event, list(
      original_publisher_date = meta$publisher_date, openalex_id = meta$openalex_id,
      indexed_year = meta$indexed_year, journal_id = meta$journal_id, journal = meta$journal,
      type = meta$openalex_type, retracted = meta$retracted, has_earlier_reproduction = earlier,
      has_i4r_overlap = any(parse_flag(rows$original_in_i4r)),
      status = if (length(reasons)) {
        paste(sort(unique(reasons), method = "radix"), collapse = ";")
      } else {
        "candidate_for_matching"
      }
    )))
    links <- tibble::tibble(
      article_id = record$article_id, source_pair_id = rows$id, replication_doi = rows$doi_r,
      source_outcome = rows$outcome, source_year = rows$year_r,
      publisher_date = dplyr::coalesce(reports$publisher_date, ""),
      publisher_type = dplyr::coalesce(reports$publisher_type, ""), is_selected = chosen,
      is_title_match = agrees, source_collection = rows$source
    )
    list(event = record, links = links)
  })
  list(events = purrr::map_dfr(results, "event"), links = purrr::map_dfr(results, "links"))
}

connect_reports <- function(events) {
  parent <- new.env(parent = emptyenv())
  root <- function(value) {
    if (!exists(value, parent, inherits = FALSE)) parent[[value]] <- value
    while (parent[[value]] != value) value <- parent[[value]]
    value
  }
  reports <- strsplit(events$reports, ";", fixed = TRUE)
  for (bundle in reports) {
    root(bundle[1])
    for (report in bundle[-1]) {
      pair <- sort(c(root(bundle[1]), root(report)), method = "radix")
      parent[[pair[2]]] <- pair[1]
    }
  }
  setNames(vapply(reports, function(bundle) root(bundle[1]), character(1)), events$article_id)
}
