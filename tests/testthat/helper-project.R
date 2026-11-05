project_root <- rprojroot::find_root(rprojroot::has_file("DESCRIPTION"))
source(file.path(project_root, "scripts", "00_config.R"))
for (module in c("data.R", "events.R", "matching.R", "analysis.R", "api.R", "metadata.R", "collection.R")) {
  source(project_file("R", module))
}
