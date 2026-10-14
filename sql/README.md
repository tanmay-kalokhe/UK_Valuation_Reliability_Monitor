# SQL

All data preparation runs in DuckDB. The stages run in numerical order.

| Folder | Purpose |
|---|---|
| `01_staging/` | Load raw files into typed staging tables, one table per source. |
| `02_matching/` | Normalise addresses and link sales to EPC certificates; report unmatched records. |
| `03_features/` | Build the modelling table (property attributes, local trends with window functions). |
| `04_monitoring/` | Monthly error, coverage and data-change summaries per area. |

## Conventions
- File names: `NN_short_description.sql`, for example `01_stg_price_paid.sql`.
- Each file creates or replaces one table or view, named after the file without the number.
- Start each file with a comment stating its inputs, its output and any assumption.
