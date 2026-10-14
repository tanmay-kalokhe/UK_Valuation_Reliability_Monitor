"""Export address-free tables for the Power BI dashboard (Weeks 1 to 3).

Planned output, written to dashboards/power_bi/data/ as Parquet files:
- dim_area, dim_local_authority, dim_property_type
- fact_sales: one row per sale with no address fields. Market and match-quality columns
  are available from Week 1; model columns (estimate, price range, error, decision) from Week 2.
- fact_monitoring: one row per local authority and month, with error, coverage and alert flags (Week 3)

The date table is built in DAX inside Power BI. Table definitions are in dashboards/power_bi/data_model.md.
"""
