"""Load raw downloads into DuckDB staging tables (Week 1).

Planned responsibilities:
- Price Paid Data: load the files and keep the release month and record status
  (A = added, C = changed, D = deleted), so the monitor can replay data as it was known at the time.
- EPC: load certificates for the study-area local authorities.
- UK House Price Index: load the regional index used by the baseline.

The SQL lives in sql/01_staging/; this module only runs it in order.
"""
