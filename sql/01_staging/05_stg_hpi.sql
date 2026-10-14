-- Inputs: UK House Price Index full file; study_area
-- Output: stg_hpi, one row per study-area local authority and month from 2019
-- Assumptions: the property-type indices are used to adjust the baseline to the sale
--              month for each property type.

CREATE OR REPLACE TABLE stg_hpi AS
SELECT
    h.regionname AS region_name,
    h.areacode AS lad_code,
    h.averageprice AS average_price,
    h.salesvolume AS sales_volume,
    h.detachedindex AS index_detached,
    h.semidetachedindex AS index_semi_detached,
    h.terracedindex AS index_terraced,
    h.flatindex AS index_flat,
    CAST(h.date AS DATE) AS month_start,
    h.index AS index_all
FROM READ_CSV('${raw_house_price_index}/*.csv', header = TRUE, normalize_names = FALSE) AS h
INNER JOIN study_area AS s ON h.areacode = s.lad_code
WHERE CAST(h.date AS DATE) >= DATE '2019-01-01';
