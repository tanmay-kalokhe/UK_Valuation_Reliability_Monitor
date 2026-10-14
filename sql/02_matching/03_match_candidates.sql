-- Inputs: match_sales, match_epc
-- Output: match_candidates, every (sale, property) pair in the same postcode that passes
--         one of three rule tiers
-- Assumptions (rule tiers, strongest first):
--   1 exact          the normalised address lines are identical
--   2 numbers_street identical non-empty identifier sets (house, flat and range numbers)
--                    and the street appears in the certificate address or the remaining
--                    words are similar (Jaro-Winkler >= 0.85)
--   3 named_house    neither address has identifiers and the words are very similar
--                    (Jaro-Winkler >= 0.92), e.g. "ROSE COTTAGE"
--   4 named_prefix   neither address has identifiers and the certificate's words start
--                    with the sale's words, e.g. "HIGHLANDS" vs "HIGHLANDS COXPARK", where
--                    the certificate adds the hamlet (common in Cornwall)
-- Thresholds are first choices; Week 2 tests them against 300 hand-checked pairs.

CREATE OR REPLACE TABLE match_candidates AS
WITH epc_addresses AS (
    SELECT DISTINCT
        property_key,
        postcode_key,
        line_norm,
        full_norm,
        address_tokens,
        address_words
    FROM match_epc
),

pairs AS (
    SELECT
        s.transaction_id,
        e.property_key,
        JARO_WINKLER_SIMILARITY(s.address_words, e.address_words) AS words_similarity,
        CASE
            WHEN s.address_norm = e.line_norm THEN 1
            WHEN
                LEN(s.address_tokens) > 0
                AND s.address_tokens = e.address_tokens
                AND (
                    (s.street_norm <> '' AND CONTAINS(e.full_norm, s.street_norm))
                    OR JARO_WINKLER_SIMILARITY(s.address_words, e.address_words) >= 0.85
                )
                THEN 2
            WHEN
                LEN(s.address_tokens) = 0
                AND LEN(e.address_tokens) = 0
                AND s.address_words <> ''
                AND JARO_WINKLER_SIMILARITY(s.address_words, e.address_words) >= 0.92
                THEN 3
            WHEN
                LEN(s.address_tokens) = 0
                AND LEN(e.address_tokens) = 0
                AND LENGTH(s.address_words) >= 4
                AND STARTS_WITH(e.address_words || ' ', s.address_words || ' ')
                THEN 4
        END AS match_tier
    FROM match_sales AS s
    INNER JOIN epc_addresses AS e ON s.postcode_key = e.postcode_key
)

SELECT
    transaction_id,
    property_key,
    match_tier,
    MAX(words_similarity) AS words_similarity
FROM pairs
WHERE match_tier IS NOT NULL
GROUP BY transaction_id, property_key, match_tier;
