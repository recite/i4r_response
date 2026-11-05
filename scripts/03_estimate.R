matched <- readRDS(file.path(derived_dir, "matched_data.rds"))
results <- estimate_study(matched)
for (name in names(results)) write_table(results[[name]], file.path(table_dir, paste0(name, ".csv")))
saveRDS(results, file.path(derived_dir, "results.rds"))

prepared <- readRDS(file.path(derived_dir, "prepared_data.rds"))
design <- assess_design(prepared)
for (name in c("coverage", "estimates", "validation", "cases", "matches")) {
  write_table(design[[name]], file.path(table_dir, paste0("design_", name, ".csv")))
}
saveRDS(design, file.path(derived_dir, "design.rds"))
