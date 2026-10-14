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
