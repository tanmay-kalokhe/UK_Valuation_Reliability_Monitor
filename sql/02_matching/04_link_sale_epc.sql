-- Inputs: match_sales, match_epc, match_candidates
-- Output:
--   match_property  the property each sale matched at its best tier, and how many
--                   distinct properties tied at that tier
--   link_sale_epc   one certificate per matched sale: the latest lodged on or before the
--                   sale date (decision D-003)
--   match_outcome   one row per Category A sale with its match status
-- Assumptions:
--   * Precision first: a sale whose best tier ties between two or more properties is
--     marked ambiguous and left unmatched rather than guessed.
--   * Status order: no_postcode, no_epc_at_postcode, no_address_match, ambiguous,
--     certificates_only_after_sale, matched.

CREATE OR REPLACE TABLE match_property AS
WITH best AS (
    SELECT
        transaction_id,
        MIN(match_tier) AS best_tier
    FROM match_candidates
    GROUP BY transaction_id
)

SELECT
    c.transaction_id,
    b.best_tier,
    ANY_VALUE(c.property_key) AS property_key,
    COUNT(DISTINCT c.property_key) AS n_properties
FROM match_candidates AS c
INNER JOIN best AS b
    ON c.transaction_id = b.transaction_id AND c.match_tier = b.best_tier
GROUP BY c.transaction_id, b.best_tier;

CREATE OR REPLACE TABLE link_sale_epc AS
WITH ranked AS (
    SELECT
        p.transaction_id,
        e.certificate_number,
        e.lodgement_date,
        s.sale_date,
        ROW_NUMBER() OVER (
            PARTITION BY p.transaction_id
            ORDER BY e.lodgement_date DESC, e.certificate_number DESC
        ) AS recency_rank
    FROM match_property AS p
    INNER JOIN match_epc AS e ON p.property_key = e.property_key
    INNER JOIN match_sales AS s ON p.transaction_id = s.transaction_id
    WHERE p.n_properties = 1 AND e.lodgement_date <= s.sale_date
)

SELECT
    transaction_id,
    certificate_number,
    lodgement_date,
    DATE_DIFF('day', lodgement_date, sale_date) AS days_before_sale
FROM ranked
WHERE recency_rank = 1;

CREATE OR REPLACE TABLE match_outcome AS
WITH epc_postcodes AS (
    SELECT DISTINCT postcode_key FROM match_epc
)

SELECT
    s.transaction_id,
    p.best_tier AS match_tier,
    l.certificate_number,
    l.days_before_sale,
    CASE
        WHEN l.certificate_number IS NOT NULL THEN 'matched'
        WHEN s.postcode_key IS NULL THEN 'no_postcode'
        WHEN ep.postcode_key IS NULL THEN 'no_epc_at_postcode'
        WHEN p.transaction_id IS NULL THEN 'no_address_match'
        WHEN p.n_properties > 1 THEN 'ambiguous'
        ELSE 'certificates_only_after_sale'
    END AS match_status
FROM match_sales AS s
LEFT JOIN match_property AS p ON s.transaction_id = p.transaction_id
LEFT JOIN link_sale_epc AS l ON s.transaction_id = l.transaction_id
LEFT JOIN epc_postcodes AS ep ON s.postcode_key = ep.postcode_key;
