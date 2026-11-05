source("scripts/00_config.R")
for (module in c("data.R", "events.R", "api.R", "metadata.R", "collection.R", "sources.R")) {
  source(project_file("R", module))
}
args <- commandArgs(trailingOnly = TRUE)
if (!length(args) || !args[1] %in% c("sources", "metadata", "pools", "histories")) {
  stop("Usage: Rscript scripts/acquire.R sources|metadata|pools|histories [--fetch] [--max-paid-usd=0]")
}
fetch <- "--fetch" %in% args
cap_arg <- grep("^--max-paid-usd=", args, value = TRUE)
cap <- if (length(cap_arg)) as.numeric(sub("^--max-paid-usd=", "", cap_arg)) else 0
if (args[1] == "sources") {
  if (!fetch) stop("Source download requires --fetch")
  collect_source_files()
} else {
  budget <- if (fetch) start_budget(file.path(source_dir, "collection_cost.json"), cap) else NULL
  switch(args[1],
    metadata = collect_metadata(budget, fetch),
    pools = collect_pools(budget, fetch),
    histories = collect_histories(budget, fetch)
  )
  if (fetch) settle_budget(budget)
}
