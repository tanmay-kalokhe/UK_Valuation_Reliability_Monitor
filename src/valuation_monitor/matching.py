"""Link Price Paid sales to EPC certificates (Week 1).

Planned responsibilities:
- Normalise addresses in SQL (sql/02_matching/) and match on postcode plus address.
- Use fuzzy matching only for records that fail the exact match.
- Keep the most recent certificate lodged on or before the sale date.
- Report unmatched records and compare them with matched ones by region and property type.
"""
