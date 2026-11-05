# Data sources and attribution

The root MIT license covers this project's code and documentation. It does not
relicense third-party data, abstracts, or evidence passages. Our original
structured annotations and numerical outputs are available under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); source terms below
continue to apply to incorporated material.

| Source | What is used | Attribution and terms |
|---|---|---|
| FORRT Library of Reproduction and Replication Attempts (FLoRA) | Original/report links, bibliographic fields and source outcome classifications | Wallrich, Röseler and colleagues (2026), [FLoRA](https://doi.org/10.17605/OSF.IO/9R62X). The [dataset page](https://forrt.org/replication-hub/flora/) specifies CC BY 4.0. |
| OpenAlex | Work identities, journal membership, citation counts and bibliographic metadata | [OpenAlex](https://help.openalex.org/data/how-its-built/) releases its database under CC0. |
| Crossref | Publisher dates, types, titles and DOI checks | [Crossref metadata terms](https://www.crossref.org/documentation/retrieve-metadata/#licensing) distinguish unrestricted factual metadata from copyrighted abstracts. |
| I4R and RePEc | Assessment inventory, report references and dated evidence | Source URLs and receipts are in `data/i4r/`. Reports and quoted text retain their original rights. |
| Earlier Recite I4R coding | Computational, robustness and materials scores | [recite/i4replication](https://github.com/recite/i4replication), pinned in `data/expansion/source_snapshots.csv`; original scores and unresolved mappings are preserved. |
| Recite research repositories | Registry, evidence annotations, matching and collection methods | [sig_fault](https://github.com/recite/sig_fault) and [propagation_of_error](https://github.com/recite/propagation_of_error); migration hashes are in `docs/migration.json`. |

The FLoRA import selects fields, normalizes DOI strings, separates source-coded
replications from reproductions, and adds timing screens. Event construction then
verifies publication metadata and retains the first recorded report year before
filtering outcomes. These are our transformations, not an endorsement or an
independent validation by FORRT. Source labels and unresolved cases remain visible.

The exact FLoRA and prior-coding revisions and source checksums are in
`data/expansion/source_snapshots.csv`. API receipts are retained alongside their
corresponding collection tables. The inherited I4R matching inputs include
OpenAlex-supplied abstracts; abstracts and evidence excerpts are third-party text
and are not covered by this project's MIT or CC BY grants. Follow each original
work's terms when reusing that text. Full papers, replication packages, API
credentials, and local working caches are not part of the release.
