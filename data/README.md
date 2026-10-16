# Data sources

Nothing in `data/` except this file and the `.gitkeep` files is committed.

**Download everything except EPC with one command** (re-runnable; finished files are skipped):
```powershell
py -3.12 -m valuation_monitor.download
```
The URLs are in `config/project_config.yaml` under `sources`. Each run records file sizes, SHA-256 hashes and dates in `docs/data_downloads.md`, so the snapshot can be verified.

| Download | Contents |
|---|---|
| Price Paid | Yearly files 2020–2026 (2020 for prior-year baseline features) plus the latest monthly update file (record status A/C/D) |
| House Price Index | Full UK HPI file, edition to July 2026 |
| Postcode lookup | ONS postcode → OA → LSOA → MSOA → local authority, with rural-urban classifications (August 2026), extracted from its zip |
| Boundaries | ONS local authorities (May 2026) and MSOAs (December 2021), generalised, as GeoJSON in WGS84 |

| Folder | Source | Where to get it | Licence and conditions |
|---|---|---|---|
| `raw/price_paid/` | HM Land Registry Price Paid Data (England and Wales) | https://www.gov.uk/government/statistical-data-sets/price-paid-data-downloads | Open Government Licence v3.0, with the required attribution. Address fields derive from Royal Mail and Ordnance Survey products, which carry extra restrictions. **Do not redistribute address-level records.** |
| `raw/epc/` | Energy Performance Certificates, domestic (England and Wales), by local authority | https://get-energy-performance-data.communities.gov.uk/ | Open Government Licence, with exceptions stated in the licence file inside each download. A GOV.UK One Login account is needed. Contains address and personal-data caveats. **Do not redistribute.** |
| `raw/house_price_index/` | UK House Price Index (HM Land Registry and ONS) | https://www.gov.uk/government/collections/uk-house-price-index-reports | Open Government Licence. Check the attribution wording on download. |
| `raw/geography/` | ONS postcode lookup (best fit, August 2026) and ONS boundaries (local authorities May 2026; MSOA December 2021) | https://geoportal.statistics.gov.uk/ | ONS geography licences (https://www.ons.gov.uk/methodology/geography/licences): Open Government Licence, with Ordnance Survey and Royal Mail attribution for postcode products. Boundaries contain OS data © Crown copyright and database right. |

## EPC: bulk CSV, not the API (decision D-014)
- **Download:** sign in with GOV.UK One Login and download the **domestic** certificates as CSV. Choose per-local-authority files if offered; otherwise take the national file. DuckDB filters it to the study area on load, so the large file is not a problem.
- **Recording:** note the download date in `docs/data_dictionary.md`. The snapshot stays fixed for the whole build, so results are reproducible.
- **What was downloaded (14 Oct 2026):** the national domestic file `domestic-csv.zip`, 8.3 GB zipped and about 98 GB unzipped. It holds `certificates-2008.csv` to `certificates-2026.csv` (93 columns, 27.5 GB) and `recommendations-*.csv` (not used).
- **Coverage:** certificates lodged from 2008, despite the service page's wording about 2012. Sales of homes with no certificate since 2008 will be unmatched, and the match-bias analysis reports this.
- **Filtering:** `py -3.12 -m valuation_monitor.ingest epc` filters the certificates to study-area postcodes one year at a time. It never unpacks the whole archive and verifies each file's checksum as it reads. Output goes to `data/interim/epc_study_area/certificates-YYYY.parquet`.
- **Useful columns:** `uprn` (a unique property reference, which identifies repeat certificates for the same home) and `transaction_type` (e.g. marketed sale).

## Folder roles
- `raw/`: files exactly as downloaded. Never edited by hand.
- `interim/`: intermediate outputs, such as cleaned or partially matched extracts.
- `processed/`: the DuckDB database (`valuation.duckdb`) and final modelling tables.

## Before downloading
- Confirm the study-area local authorities in `config/project_config.yaml`.
- Record the download date and file names in `docs/data_dictionary.md`.
- Re-read each licence on its download page, since terms can change.
