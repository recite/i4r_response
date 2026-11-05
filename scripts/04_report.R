prepared <- readRDS(file.path(derived_dir, "prepared_data.rds"))
matched <- readRDS(file.path(derived_dir, "matched_data.rds"))
results <- readRDS(file.path(derived_dir, "results.rds"))
write_results(prepared, matched, results)
