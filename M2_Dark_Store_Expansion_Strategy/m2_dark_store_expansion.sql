-- ================================================================
-- Quick Commerce Wars
-- Module 2: Dark Store Expansion Analysis
-- ================================================================
-- ================================================================


-- ================================================================
-- STEP 0: Table setup (run once)
-- ================================================================

CREATE TABLE IF NOT EXISTS dark_stores (
    store_id    VARCHAR(50),
    store_name  VARCHAR(100),
    company     VARCHAR(50),
    city        VARCHAR(50),
    state       VARCHAR(50),
    lat         NUMERIC(12,8),
    lng         NUMERIC(12,8)
);

CREATE TABLE IF NOT EXISTS india_census_urban (
    state_code          INT,
    district_code       INT,
    district_name       VARCHAR(100),
    urban_population    BIGINT,
    households          BIGINT,
    literate_pop        BIGINT,
    illiterate_pop      BIGINT,
    total_workers       BIGINT,
    service_workers     BIGINT,
    non_workers         BIGINT,
    literacy_rate       NUMERIC(5,2),
    avg_household_size  NUMERIC(5,2)
);

-- ================================================================
-- STEP 1: Sanity check
-- ================================================================

SELECT
    company,
    COUNT(*)             AS total_stores,
    COUNT(DISTINCT city) AS cities_covered
FROM dark_stores
WHERE city != 'Unknown'
GROUP BY company
ORDER BY total_stores DESC;

-- Expected:
--   Blinkit          ~1,600 stores
--   Swiggy Instamart ~1,600 stores
--   Zepto            ~800 stores


-- ================================================================
-- QUERY 1: Store Count by City and Company (pivot format)
-- ================================================================
-- What it does: Shows how many stores each company has per city
--               in a single wide-format table.
-- ================================================================

SELECT
    city,
    COUNT(*) FILTER (WHERE company = 'Blinkit')          AS blinkit_stores,
    COUNT(*) FILTER (WHERE company = 'Swiggy Instamart') AS swiggy_stores,
    COUNT(*) FILTER (WHERE company = 'Zepto')            AS zepto_stores,
    COUNT(*)                                             AS total_stores
FROM dark_stores
WHERE city != 'Unknown'
GROUP BY city
ORDER BY total_stores DESC;


-- ================================================================
-- QUERY 2: Top Cities Per Company (RANK window function)
-- ================================================================
-- What it does: Ranks each company's cities by store count.
--               Useful for understanding where each company
--               has concentrated its investment.
-- ================================================================

SELECT
    company,
    city,
    COUNT(*)                                   AS stores,
    RANK() OVER (
        PARTITION BY company
        ORDER BY COUNT(*) DESC
    )                                          AS city_rank
FROM dark_stores
WHERE city != 'Unknown'
GROUP BY company, city
HAVING COUNT(*) >= 3
ORDER BY company, city_rank;


-- ================================================================
-- QUERY 3: State-Level Coverage
-- ================================================================
-- What it does: Aggregates to state level — useful for a
--               choropleth map in Tableau showing coverage
--               by state rather than city.
-- ================================================================

SELECT
    state,
    COUNT(*) FILTER (WHERE company = 'Blinkit')          AS blinkit_stores,
    COUNT(*) FILTER (WHERE company = 'Swiggy Instamart') AS swiggy_stores,
    COUNT(*) FILTER (WHERE company = 'Zepto')            AS zepto_stores,
    COUNT(*)                                             AS total_stores,
    COUNT(DISTINCT city)                                 AS cities_covered
FROM dark_stores
WHERE state IS NOT NULL
  AND state NOT IN ('Unknown', '')
GROUP BY state
ORDER BY total_stores DESC;


-- ================================================================
-- QUERY 4: Delhi/NCR Competitive Gap
-- ================================================================
-- What it does: Computes each company's store share within the
--               Delhi/NCR metro — the single most important
--               market in Indian quick commerce.
-- ================================================================

SELECT
    company,
    COUNT(*)                                              AS stores_in_ncr,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2)  AS ncr_share_pct
FROM dark_stores
WHERE city IN ('Delhi/NCR', 'Delhi', 'Gurgaon', 'Gurugram',
               'Noida', 'Greater Noida', 'Faridabad', 'Ghaziabad')
GROUP BY company
ORDER BY stores_in_ncr DESC;


-- ================================================================
