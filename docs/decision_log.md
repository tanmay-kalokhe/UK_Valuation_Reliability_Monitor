# Decision log

Each entry records a design decision, the reason for it, and the date. Add new entries at the bottom.

| ID | Date | Decision | Reason |
|---|---|---|---|
| D-001 | 2026-10-14 | Scope is England and Wales, starting with 5 to 10 local authorities and sales from 2021. | Price Paid Data covers England and Wales; a small area keeps the first build fast. |
| D-002 | 2026-10-14 | Keep Price Paid Category A (standard) sales only. | Category B includes repossessions and other non-market transfers. |
| D-003 | 2026-10-14 | Use the most recent EPC lodged on or before the sale date. | A later certificate can reflect post-sale changes and would leak future information. |
| D-004 | 2026-10-14 | Model log price; compare against an HPI-indexed district median baseline. | Prices are skewed; the baseline mirrors a simple industry method. |
| D-005 | 2026-10-14 | Target 90% interval coverage, reported by area, property type and month. | Average coverage can hide areas where the intervals fail. |
| D-006 | 2026-10-14 | The public demo and repository contain no address-level data. | Price Paid address fields and EPC data carry reuse restrictions. |
| D-007 | 2026-10-14 | The intended user is a mortgage lender's valuation team deciding whether to accept an automated valuation or refer the property to a surveyor. | Gives every result a business decision; chosen by Tanmay. |
| D-008 | 2026-10-14 | Study area: Manchester, Trafford, Leeds, Milton Keynes, Camden, Cornwall and Cardiff. | Contrasting markets (city, suburb, new town, high-value London, rural/coastal, Wales) make area-level reliability meaningful. All seven had unchanged boundaries throughout the period. |
| D-009 | 2026-10-14 | SQL rule-based matching is the primary method; Splink probabilistic matching is the comparison, judged on a hand-checked sample of 300. | Shows both approaches and measures their trade-off rather than assuming one is better. |
| D-010 | 2026-10-14 | Maps use open ONS boundaries: local authority for monthly alerts, MSOA for pooled error and coverage. | Postcode-district boundaries are not open data, and monthly MSOA sample sizes are too small for alerts. |
| D-011 | 2026-10-14 | The Streamlit demo is hosted publicly on Streamlit Community Cloud; users enter property characteristics and a postcode district, never an address. | A public link for the CV without redistributing address-level data. |
| D-012 | 2026-10-14 | Python 3.12 virtual environment; exact versions recorded in requirements-lock.txt (pandas 3.x, DuckDB 1.5, Splink 5). | Reproducibility; ML library wheels lag behind Python 3.14. |
| D-013 | 2026-10-14 | LTV-aware decision rule: accept when (LTV × estimate) ÷ lower end of the price range ≤ stress cap (default 100%, default LTV 75%); otherwise refer to a surveyor. Exposed as LTV and stress-cap inputs in Power BI and Streamlit. | Lenders tolerate more valuation uncertainty on low-LTV loans. The rule links the price range directly to the lender's risk (negative equity at the pessimistic value) with no arbitrary tiers. Defaults are illustrative, not lender policy. |
| D-014 | 2026-10-14 | EPC data comes from the bulk CSV download, loaded into DuckDB and filtered to the study area; the API is not used in the core build. | A fixed snapshot is reproducible, avoids paging and rate limits, and keeps the work in SQL. Coverage limits of the dataset are reported in the match-bias analysis. |
| D-015 | 2026-10-14 | Data snapshot frozen for the build: Price Paid to 28 Aug 2026 (yearly files 2020–2026 plus the monthly update), UK HPI to Jul 2026, ONS postcode lookup Aug 2026, boundaries May 2026 (local authorities) and Dec 2021 (MSOA). Hashes in docs/data_downloads.md. | A fixed snapshot keeps every result reproducible. The monthly update file already holds 3,095 changed and 1,488 deleted records, so revisions are real and the replay must handle them. |
| D-016 | 2026-10-14 | Address matching: four SQL rule tiers within the same postcode (exact; same house/flat identifiers and street; similar house name; house name plus hamlet). Ties between properties are left unmatched. | Precision first: a wrong certificate gives wrong floor areas, which is worse than none. Result: 94.8% of Category A sales linked; tiers and thresholds are re-tested on 300 hand-checked pairs in Week 2. |
| D-017 | 2026-10-14 | Power BI area key is local authority + postcode district (e.g. `E08000035\|LS6`). | A postcode district can cross a local-authority boundary, so the district alone is not a unique key. |
