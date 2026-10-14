-- Inputs: none
-- Output: three SQL macros used by the matching stage
-- Assumptions:
--   * normalise_address: upper case, punctuation to spaces, APARTMENT/APT/FLT -> FLAT,
--     single spaces. "42-43" becomes "42 43", so ranges compare as two numbers.
--   * address_tokens: the sorted house/flat identifiers in an address: numbers with an
--     optional letter suffix ("12A"), letter-prefixed flat numbers ("B1002") and lettered
--     flats ("FLAT D" -> "_D").
--   * address_words: what is left once identifiers, the word FLAT and single letters are
--     removed, e.g. building and street names, for fuzzy comparison.

CREATE OR REPLACE MACRO NORMALISE_ADDRESS(address_text) AS
TRIM(
    REGEXP_REPLACE(
        REGEXP_REPLACE(
            REGEXP_REPLACE(UPPER(COALESCE(address_text, '')), '[^A-Z0-9 ]', ' ', 'g'),
            '\b(APARTMENT|APT|FLT)\b', 'FLAT', 'g'
        ),
        '\s+', ' ', 'g'
    )
);

CREATE OR REPLACE MACRO ADDRESS_TOKENS(normalised) AS
LIST_SORT(
    REGEXP_EXTRACT_ALL(
        REGEXP_REPLACE(normalised, '\b(FLAT|UNIT|MAISONETTE) ([A-Z])\b', '\1 _\2', 'g'),
        '\b(\d+[A-Z]?|[A-Z]\d+|_[A-Z])\b'
    )
);

CREATE OR REPLACE MACRO ADDRESS_WORDS(normalised) AS
TRIM(
    REGEXP_REPLACE(
        REGEXP_REPLACE(normalised, '\b(\d+[A-Z]?|[A-Z]\d+|FLAT|[A-Z])\b', ' ', 'g'),
        '\s+', ' ', 'g'
    )
);
