prepared <- readRDS(file.path(derived_dir, "prepared_data.rds"))
matched <- match_events(prepared$registry$events, prepared$inputs)
for (name in names(matched)) write_table(matched[[name]], file.path(table_dir, paste0(name, ".csv")))
saveRDS(matched, file.path(derived_dir, "matched_data.rds"))
