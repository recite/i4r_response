upsert_records <- function(old, new, key) {
  if (!nrow(new)) {
    return(old)
  }
  new <- dplyr::mutate(new, dplyr::across(dplyr::everything(), as.character))
  old <- dplyr::mutate(old, dplyr::across(dplyr::everything(), as.character))
  dplyr::bind_rows(dplyr::anti_join(old, new, by = key), new) |>
    dplyr::mutate(dplyr::across(dplyr::everything(), ~ dplyr::coalesce(.x, "")))
}

sample_comparison_pool <- function(journal_id, year, kind, budget, fetch = FALSE) {
  query <- paste0("primary_location.source.id:", journal_id, ",publication_year:", year, ",type:", kind)
  pool_id <- paste0("sample_", substr(digest::digest(query, algo = "sha256", serialize = FALSE), 1, 16))
  count <- cached_json(api_url("works", filter = query, per_page = 1, select = "id"), "pools", fetch, budget)
  sample <- cached_json(
    api_url("works",
      filter = query, sample = comparison_sample_size, seed = comparison_seed,
      per_page = comparison_sample_size,
      select = "id,doi,title,publication_year,publication_date,type,is_retracted,primary_location"
    ),
    "pools", fetch, budget
  )
  works <- sample$payload$results
  ids <- vapply(works, function(work) work$id, character(1))
  if (length(works) != min(comparison_sample_size, count$payload$meta$count) || anyDuplicated(ids)) {
    stop("Incomplete or duplicate candidate sample")
  }
  for (work in works) {
    if (
      as.character(work$publication_year) != year || work$type != kind ||
        work$primary_location$source$id != journal_id
    ) {
      stop("Candidate outside requested journal/year")
    }
  }
  list(pool = tibble::tibble(
    event_id = pool_id, journal_id, year, type = kind, status = "complete", query_filter = query,
    pool_count = count$payload$meta$count, sample_size = length(works), seed = comparison_seed,
    complete_pool = count$payload$meta$count <= comparison_sample_size, detail = ""
  ), works = works)
}

work_to_article <- function(work) {
  doi <- normalize_doi(work$doi %||% "")
  journal <- work$primary_location$source %||% list()
  tibble::tibble(
    article_id = if (nzchar(doi)) make_paper_id(doi) else paste0("work_", basename(work$id)),
    title = work$title %||% "", doi = doi, openalex_id = work$id,
    journal = journal$display_name %||% "", journal_id = journal$id %||% "",
    publication_date = "", publication_year = "", indexed_publication_date = work$publication_date %||% "",
    indexed_publication_year = as.character(work$publication_year), publication_date_source = "", type = work$type,
    abstract = "", identity_verified = "yes",
    retracted = if (is.null(work$is_retracted)) "unknown" else if (work$is_retracted) "yes" else "no",
    retraction_date = "", retraction_source = ""
  )
}

collect_pools <- function(budget, fetch = FALSE) {
  inputs <- read_study_inputs()
  events <- build_events(inputs$flora_candidates, inputs$metadata)$events
  keys <- events |>
    dplyr::filter(status == "candidate_for_matching") |>
    dplyr::distinct(journal_id, indexed_year, type) |>
    dplyr::arrange(journal_id, indexed_year, type, .locale = "C")
  pools <- inputs$comparison_pools
  articles <- inputs$comparison_articles
  members <- inputs$comparison_members
  complete <- with(pools[pools$status == "complete", ], paste(journal_id, year, type, sep = "|"))
  for (i in seq_len(nrow(keys))) {
    key <- keys[i, ]
    if (paste(key$journal_id, key$indexed_year, key$type, sep = "|") %in% complete) next
    result <- sample_comparison_pool(key$journal_id, key$indexed_year, key$type, budget, fetch)
    found <- purrr::map_dfr(result$works, work_to_article)
    pools <- upsert_records(pools, result$pool, "event_id")
    new_members <- found |> dplyr::transmute(pool_id = result$pool$event_id, article_id, openalex_id)
    members <- upsert_records(members, new_members, c("pool_id", "article_id", "openalex_id"))
    found <- dplyr::distinct(found, article_id, .keep_all = TRUE)
    articles <- upsert_records(articles, found, "article_id")
    write_table(pools, file.path(source_dir, "comparison_pools.csv"))
    write_table(members, file.path(source_dir, "comparison_members.csv"))
    write_table(articles, file.path(source_dir, "comparison_articles.csv"))
  }
  publisher <- read_source(file.path(source_dir, "comparison_metadata.csv"))
  missing <- setdiff(articles$doi[nzchar(articles$doi)], publisher$doi[publisher$crossref_status == "complete"])
  if (length(missing)) publisher <- upsert_records(publisher, lookup_crossref(missing, fetch), "doi")
  write_table(publisher, file.path(source_dir, "comparison_metadata.csv"))
  known <- unique(c(
    normalize_doi(inputs$flora_candidates$doi_o), normalize_doi(inputs$flora_candidates$doi_r),
    read_source(file.path(i4r_dir, "articles.csv"))$doi
  ))
  known <- known[nzchar(known)]
  manual <- read_source(file.path(source_dir, "comparison_manual_exclusions.csv"))$article_id
  exclusions <- list()
  for (i in seq_len(nrow(articles))) {
    article <- articles[i, ]
    date <- publisher[match(article$doi, publisher$doi), ]
    reasons <- character()
    if (article$article_id %in% manual) reasons <- c(reasons, "reviewed_nonresearch")
    if (article$doi %in% known) reasons <- c(reasons, "known_assessed_original_or_assessment_report")
    if (article$retracted != "no") reasons <- c(reasons, "current_retraction_flag")
    if (is.na(date$publisher_date) || !nzchar(date$publisher_date) || date$publisher_type != "journal-article") {
      reasons <- c(reasons, "publisher_journal_date_unavailable")
    }
    if (is.na(date$publisher_title) || !same_title(article$title, date$publisher_title)) {
      reasons <- c(reasons, "publisher_title_review_required")
    }
    title <- normalize_title(article$title)
    nonresearch <- paste0(
      "^(frontmatter|backmatter|editorial|erratum|corrigendum|retraction|",
      "correctionto|acknowledg|listofreviewers|recentreferees|indexof|annualreport)"
    )
    if (stringr::str_detect(title, nonresearch)) {
      reasons <- c(reasons, "nonresearch_title")
    }
    if (length(reasons)) {
      exclusions[[length(exclusions) + 1L]] <- tibble::tibble(
        article_id = article$article_id, reasons = paste(reasons, collapse = ";"), title = article$title
      )
    }
    articles$publication_date[i] <- dplyr::coalesce(date$publisher_date, "")
    articles$publication_year[i] <- substr(articles$publication_date[i], 1, 4)
    articles$publication_date_source[i] <- dplyr::coalesce(date$crossref_record_url, "")
  }
  write_table(articles, file.path(source_dir, "comparison_articles.csv"))
  write_table(dplyr::bind_rows(exclusions), file.path(source_dir, "comparison_exclusions.csv"))
  write_metadata_receipts()
}

parse_year_counts <- function(payload, last_year = last_citation_year) {
  groups <- payload$group_by
  years <- vapply(groups, function(group) as.character(group$key), character(1))
  counts <- vapply(groups, function(group) as.numeric(group$count), numeric(1))
  if (
    anyDuplicated(years) || any(!grepl("^[0-9]+$", years)) ||
      any(as.integer(years) < 1500 | as.integer(years) > last_year)
  ) {
    stop("Invalid citing years")
  }
  if (
    anyNA(counts) || any(counts < 0 | counts %% 1 != 0) ||
      sum(counts) != payload$meta$count
  ) {
    stop("Year counts do not reconcile")
  }
  setNames(counts, years)
}

make_history_roster <- function() {
  inputs <- read_study_inputs()
  events <- build_events(inputs$flora_candidates, inputs$metadata)$events
  originals <- events |>
    dplyr::filter(status == "candidate_for_matching") |>
    dplyr::transmute(article_id,
      role = "original", work_ids = openalex_id,
      indexed_publication_year = indexed_year, identity_verified = "yes"
    )
  aliases <- inputs$comparison_members |>
    dplyr::group_by(article_id) |>
    dplyr::summarise(
      work_ids = paste(sort(unique(openalex_id), method = "radix"), collapse = "|"),
      first_pool = min(pool_id), .groups = "drop"
    )
  controls <- inputs$comparison_articles |>
    dplyr::filter(!article_id %in% inputs$comparison_exclusions$article_id) |>
    dplyr::left_join(aliases, by = "article_id", relationship = "one-to-one") |>
    dplyr::arrange(first_pool, article_id, .locale = "C") |>
    dplyr::transmute(article_id, role = "control", work_ids, indexed_publication_year, identity_verified)
  dplyr::bind_rows(originals, controls)
}

acquire_history <- function(row, budget, fetch = FALSE) {
  query <- api_url("works", filter = paste0(
    "cites:", row$work_ids, ",type:article|review,to_publication_date:",
    last_citation_year, "-12-31"
  ), group_by = "publication_year", per_page = 200)
  response <- cached_json(query, "citations", fetch, budget)
  counts <- parse_year_counts(response$payload)
  first <- as.integer(row$indexed_publication_year)
  start <- min(first, as.integer(names(counts)))
  years <- if (start > last_citation_year) integer() else seq.int(start, last_citation_year)
  values <- counts[as.character(years)]
  values[is.na(values)] <- 0
  list(
    annual = tibble::tibble(
      article_id = row$article_id, year = years, citations = unname(values),
      status = "complete", pre_indexed_publication = years < first
    ),
    receipt = tibble::tibble(
      article_id = row$article_id, role = row$role, work_ids = row$work_ids,
      indexed_publication_year = first, panel_first_year = start, api_count = sum(counts), sum_counts = sum(counts),
      before_publication = sum(counts[as.integer(names(counts)) < first]), status = "complete", detail = "",
      source_url = query, source_path = sub(paste0(project_root, "/"), "", response$path, fixed = TRUE),
      source_sha256 = response$receipt$sha256, retrieved_at = response$receipt$retrieved_at
    )
  )
}

collect_histories <- function(budget, fetch = FALSE) {
  roster <- make_history_roster()
  receipts <- read_source(file.path(source_dir, "citation_totals.csv"))
  annual <- read_source(file.path(source_dir, "citations.csv"))
  complete <- receipts$article_id[receipts$status == "complete"]
  pending <- roster[!roster$article_id %in% complete, ]
  stopped <- FALSE
  batches <- split(seq_len(nrow(pending)), ceiling(seq_len(nrow(pending)) / 100L))
  for (batch in batches) {
    new_annual <- list()
    new_receipts <- list()
    for (i in batch) {
      row <- pending[i, ]
      result <- tryCatch(acquire_history(row, budget, fetch && !stopped), error = function(error) error)
      if (inherits(result, "error")) {
        detail <- conditionMessage(result)
        if (detail == "budget_stop") stopped <- TRUE
        if (stopped && detail == "response_not_cached") detail <- "budget_stop"
        receipt <- row |> dplyr::mutate(status = "unavailable", detail = detail)
      } else {
        receipt <- result$receipt
        new_annual[[length(new_annual) + 1L]] <- result$annual
      }
      new_receipts[[length(new_receipts) + 1L]] <- receipt
    }
    annual <- upsert_records(annual, dplyr::bind_rows(new_annual), c("article_id", "year"))
    receipts <- upsert_records(receipts, dplyr::bind_rows(new_receipts), "article_id")
    validate_histories(annual, receipts)
    write_table(annual, file.path(source_dir, "citations.csv"))
    write_table(receipts, file.path(source_dir, "citation_totals.csv"))
    message("Histories checked: ", max(batch), "/", nrow(pending))
  }
  if (fetch) settle_budget(budget)
}
