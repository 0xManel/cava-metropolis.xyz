# Reports Organization

This folder keeps human-readable inputs and audit outputs used during catalog enrichment.

## Main Files (kept at root)

- `cata_lote_*.txt`: source batches used for tasting/critics imports.
- `cata_lote_*_raw.txt`: raw extraction snapshots.
- `vinhos_faltantes_notas_card_criticos.csv`: master list used for pending completion work.
- `vinhos_sem_nota_e_sem_card_resumo.csv`: quick check list for wines missing both fields.

## Generated Artifacts

Auxiliary generated files were grouped under:

- `reports/_generated/import/`: technical import logs (`*_import_report.json`, `*_import_unmatched.csv`, csv parsing outputs).
- `reports/_generated/reimport/`: reimport validation logs (`*_reimport_report.json`, `*_reimport_unmatched.csv`).
- `reports/_generated/summaries/`: intermediate/auxiliary summary CSVs.

`reports/_generated/` is intentionally ignored in git to keep history clean.
