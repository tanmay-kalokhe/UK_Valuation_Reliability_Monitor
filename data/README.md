# Data sources

Nothing in `data/` except this file and the `.gitkeep` files is committed. Download the sources into the folders below; scripts read them from there.

| Folder | Source | Where to get it | Licence and conditions |
|---|---|---|---|
| `raw/price_paid/` | HM Land Registry Price Paid Data (England and Wales) | https://www.gov.uk/government/statistical-data-sets/price-paid-data-downloads | Open Government Licence v3.0, with the required attribution. Address fields derive from Royal Mail and Ordnance Survey products, which carry extra restrictions. **Do not redistribute address-level records.** |
| `raw/epc/` | Energy Performance Certificates, domestic (England and Wales), by local authority | https://get-energy-performance-data.communities.gov.uk/ | Open Government Licence, with exceptions stated in the licence file inside each download. A GOV.UK One Login account is needed. Contains address and personal-data caveats. **Do not redistribute.** |
| `raw/house_price_index/` | UK House Price Index (HM Land Registry and ONS) | https://www.gov.uk/government/collections/uk-house-price-index-reports | Open Government Licence. Check the attribution wording on download. |
| `raw/geography/` | Postcode-to-local-authority lookup (e.g. ONS Postcode Directory) | https://geoportal.statistics.gov.uk/ | Check the licence on the product page: it includes Royal Mail and Ordnance Survey terms. |

## EPC: bulk CSV, not the API (decision D-014)
- **Download:** sign in with GOV.UK One Login and download the **domestic** certificates as CSV. Choose per-local-authority files if offered; otherwise take the national file. DuckDB filters it to the study area on load, so the large file is not a problem.
- **Recording:** note the download date in `docs/data_dictionary.md`. The snapshot stays fixed for the whole build, so results are reproducible.
- **Coverage:** the service page says the data includes certificates registered since 2012. Sales whose only certificate is older will be unmatched. The match-bias analysis reports this rather than hiding it.

## Folder roles
- `raw/`: files exactly as downloaded. Never edited by hand.
- `interim/`: intermediate outputs, such as cleaned or partially matched extracts.
- `processed/`: the DuckDB database (`valuation.duckdb`) and final modelling tables.

## Before downloading
- Confirm the study-area local authorities in `config/project_config.yaml`.
- Record the download date and file names in `docs/data_dictionary.md`.
- Re-read each licence on its download page, since terms can change.
