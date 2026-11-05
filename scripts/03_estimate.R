matched <- readRDS(file.path(derived_dir, "matched_data.rds"))
results <- estimate_study(matched)
for (name in names(results)) write_table(results[[name]], file.path(table_dir, paste0(name, ".csv")))
saveRDS(results, file.path(derived_dir, "results.rds"))
