-- Inputs: stg_hpi
-- Output: feat_hpi, one row per local authority, property type and month, with the UK HPI
--         index for that property type
-- Assumptions: the Price Paid type codes map to the HPI type indices (D detached,
--              S semi-detached, T terraced, F flat). Category A sales have no type O.

CREATE OR REPLACE TABLE feat_hpi AS
SELECT
    h.lad_code,
    h.month_start,
    t.property_type,
    CASE t.property_type
        WHEN 'D' THEN h.index_detached
        WHEN 'S' THEN h.index_semi_detached
        WHEN 'T' THEN h.index_terraced
        WHEN 'F' THEN h.index_flat
    END AS hpi_index
FROM stg_hpi AS h
CROSS JOIN (VALUES ('D'), ('S'), ('T'), ('F')) AS t (property_type);
