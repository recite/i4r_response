extract_publisher_date <- function(work) {
  dates <- vapply(c("published-online", "published-print", "published"), function(field) {
    parts <- unlist(work[[field]][["date-parts"]][[1]])
    if (!length(parts) || parts[1] < 1500 || parts[1] > 2026) {
      return(NA_character_)
    }
    paste(c(sprintf("%04d", parts[1]), sprintf("%02d", parts[-1])), collapse = "-")
  }, character(1))
  if (all(is.na(dates))) "" else min(dates, na.rm = TRUE)
}

parse_crossref <- function(doi, work, receipt) {
  if (normalize_doi(work$DOI %||% "") != doi) stop("Crossref DOI mismatch")
  tibble::tibble(
    doi,
    crossref_status = "complete", publisher_date = extract_publisher_date(work),
    publisher_type = work$type %||% "", publisher_title = paste(unlist(work$title), collapse = "; "),
    publisher_journal = paste(unlist(work[["container-title"]]), collapse = "; "),
    crossref_record_url = paste0("https://api.crossref.org/works/", utils::URLencode(doi, reserved = TRUE)),
    crossref_sha256 = receipt$sha256, crossref_retrieved_at = receipt$retrieved_at, detail = ""
  )
}

lookup_crossref <- function(dois, fetch = FALSE) {
  batches <- split(dois, ceiling(seq_along(dois) / 50L))
  purrr::map_dfr(batches, function(batch) {
    # A comma in a DOI is also a Crossref filter delimiter.
    if (any(grepl(",", batch, fixed = TRUE))) {
      return(purrr::map_dfr(batch, function(doi) {
        tryCatch(
          {
            url <- paste0("https://api.crossref.org/works/", utils::URLencode(doi, reserved = TRUE))
            response <- cached_json(url, "crossref", fetch)
            parse_crossref(doi, response$payload$message, response$receipt)
          },
          error = function(error) {
            tibble::tibble(
              doi = doi, crossref_status = "unavailable", detail = conditionMessage(error)
            )
          }
        )
      }))
    }
    url <- httr2::request("https://api.crossref.org/works") |>
      httr2::req_url_query(
        filter = paste0("doi:", batch, collapse = ","), rows = 100,
        select = "DOI,title,type,published,published-online,published-print,container-title"
      ) |>
      purrr::pluck("url")
    tryCatch(
      {
        response <- cached_json(url, "crossref", fetch)
        works <- response$payload$message$items
        found <- vapply(works, function(work) normalize_doi(work$DOI), character(1))
        if (
          length(works) != response$payload$message[["total-results"]] || anyDuplicated(found) ||
            !all(found %in% batch)
        ) {
          stop("Truncated or conflicting Crossref batch")
        }
        purrr::map_dfr(batch, function(doi) {
          at <- match(doi, found)
          if (is.na(at)) {
            return(tibble::tibble(doi = doi, crossref_status = "unavailable", detail = "doi_not_returned"))
          }
          parse_crossref(doi, works[[at]], response$receipt)
        })
      },
      error = function(error) {
        tibble::tibble(
          doi = batch, crossref_status = "unavailable", detail = conditionMessage(error)
        )
      }
    )
  })
}

parse_openalex <- function(payload, requested) {
  works <- payload$results
  if (length(works) != payload$meta$count) stop("Truncated OpenAlex batch")
  dois <- vapply(works, function(work) normalize_doi(work$doi %||% ""), character(1))
  accepted <- dois %in% requested
  if (anyDuplicated(dois[accepted])) stop("Multiple OpenAlex records for DOI")
  setNames(works[accepted], dois[accepted])
}

openalex_fields <- function(work, receipt) {
  journal <- work$primary_location$source %||% list()
  tibble::tibble(
    openalex_id = work$id %||% "", indexed_year = as.character(work$publication_year %||% ""),
    indexed_date = work$publication_date %||% "", openalex_type = work$type %||% "",
    openalex_title = work$title %||% "", journal_id = journal$id %||% "", journal = journal$display_name %||% "",
    retracted = if (is.logical(work$is_retracted) && length(work$is_retracted) == 1L) {
      if (work$is_retracted) "True" else "False"
    } else {
      ""
    },
    openalex_record_url = if (is.null(work$id)) {
      ""
    } else {
      sub("https://openalex.org/", "https://api.openalex.org/works/", work$id, fixed = TRUE)
    },
    openalex_sha256 = receipt$sha256 %||% "", openalex_retrieved_at = receipt$retrieved_at %||% ""
  )
}

collect_metadata <- function(budget, fetch = FALSE) {
  pairs <- read_source(file.path(source_dir, "flora_candidates.csv"))
  pairs <- pairs[pairs$type == "replication", ]
  dois <- sort(unique(normalize_doi(c(pairs$doi_o, pairs$doi_r))), method = "radix")
  dois <- dois[nzchar(dois)]
  path <- file.path(source_dir, "metadata.csv")
  existing <- read_source(path)
  missing <- setdiff(dois, existing$doi[existing$crossref_status == "complete"])
  if (length(missing)) {
    found <- lookup_crossref(missing, fetch)
    for (i in seq_len(nrow(found))) {
      at <- match(found$doi[i], existing$doi)
      if (is.na(at)) {
        existing[nrow(existing) + 1L, ] <- ""
        at <- nrow(existing)
      }
      for (field in names(found)) existing[[field]][at] <- dplyr::coalesce(found[[field]][i], "")
    }
    write_table(existing, path)
  }
  missing <- setdiff(dois, existing$doi[nzchar(existing$openalex_id)])
  for (batch in split(missing, ceiling(seq_along(missing) / 50L))) {
    values <- ifelse(grepl(",", batch, fixed = TRUE), paste0('"', batch, '"'), batch)
    response <- cached_json(
      api_url("works",
        filter = paste0("doi:", paste(values, collapse = "|")),
        per_page = 100, select = "id,doi,title,publication_year,publication_date,type,is_retracted,primary_location"
      ),
      "openalex", fetch, budget
    )
    works <- parse_openalex(response$payload, batch)
    for (doi in names(works)) {
      fields <- openalex_fields(works[[doi]], response$receipt)
      at <- match(doi, existing$doi)
      for (field in names(fields)) existing[[field]][at] <- fields[[field]]
    }
    write_table(existing, path)
  }
  write_metadata_receipts()
}
