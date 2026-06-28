-- ================================================================
-- Quick Commerce Wars
-- Module 1: Executive Strategy Dashboard
-- ================================================================
--
-- Business question:
--   How do Blinkit, Zepto, and Swiggy Instamart compare on
--   market share, revenue, delivery speed, and customer ratings?
--

-- ================================================================
-- STEP 0: Table setup (run once before importing data)
-- ================================================================

CREATE TABLE IF NOT EXISTS qc_main (
    order_id                BIGINT PRIMARY KEY,
    company                 VARCHAR(50),
    city                    VARCHAR(50),
    customer_age            INT,
    order_value             NUMERIC(10,2),
    delivery_time_min       NUMERIC(6,2),
    distance_km             NUMERIC(6,2),
    items_count             INT,
    product_category        VARCHAR(50),
    payment_method          VARCHAR(50),
    customer_rating         NUMERIC(3,2),
    is_discounted           INT,             -- 1 = discounted, 0 = full price
    delivery_partner_rating NUMERIC(3,2),
    order_value_bucket      VARCHAR(30),     -- Low / Medium / High / Premium
    delivery_speed_bucket   VARCHAR(30),     -- Fast / Standard / Slow
    distance_bucket         VARCHAR(30),     -- Short / Medium / Long
    revenue_per_km          NUMERIC(10,2),
    is_high_value           INT              -- 1 if order_value > 75th percentile
);

-- After creating the table, import qc_main_cleaned.csv via:
-- pgAdmin → right-click table → Import/Export Data → CSV → Header ON


-- ================================================================
-- STEP 1: Sanity check — verify row counts before running queries
-- ================================================================

SELECT
    company,
    COUNT(*) AS total_orders
FROM qc_main
GROUP BY company
ORDER BY total_orders DESC;

-- Expected output:
--   Blinkit          ~125,000 rows
--   Zepto            ~125,000 rows
--   Swiggy Instamart ~125,000 rows
-- If counts are way off, the import may have failed — re-import.


-- ================================================================
-- QUERY 1: Market Share
-- ================================================================
-- Metric  : Orders per company as % of total market
-- Window  : SUM(COUNT(*)) OVER () = grand total across all companies
-- Export  : m1_market_share.csv
-- Tableau : Pie chart or bar chart — company on axis, market_share_pct on value
-- ================================================================

SELECT
    company,
    COUNT(*)                                                  AS total_orders,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2)       AS market_share_pct
FROM qc_main
GROUP BY company
ORDER BY total_orders DESC;


-- ================================================================
-- QUERY 2: Revenue & Average Order Value
-- ================================================================
-- Metric  : Total revenue (in ₹ millions), AOV, median order value
-- Note    : PERCENTILE_CONT(0.5) = median. ::NUMERIC cast required
--           in PostgreSQL for WITHIN GROUP on NUMERIC columns.
-- Export  : m1_revenue_aov.csv
-- Tableau : Grouped bar chart — company vs revenue_millions and avg_order_value
-- ================================================================

SELECT
    company,
    ROUND(SUM(order_value) / 1000000.0, 2)                    AS revenue_millions,
    ROUND(AVG(order_value), 2)                                 AS avg_order_value,
    ROUND(PERCENTILE_CONT(0.5)
          WITHIN GROUP (ORDER BY order_value::NUMERIC), 2)     AS median_order_value,
    COUNT(*) FILTER (WHERE is_discounted = 1)                  AS discounted_orders,
    ROUND(COUNT(*) FILTER (WHERE is_discounted = 1)
          * 100.0 / COUNT(*), 2)                               AS discount_rate_pct
FROM qc_main
GROUP BY company
ORDER BY revenue_millions DESC;


-- ================================================================
-- QUERY 3: Delivery Performance (core KPI)
-- ================================================================
-- Metric  : Avg delivery, P50, P90, slow order rate (>30 min)
-- Note    : P90 is the most important metric here — it captures
--           the worst-10% experience that drives churn.
--           Zepto's P90 (~14 min) vs Swiggy's P90 (~28 min) is
--           the most striking finding in this module.
-- Export  : m1_delivery_kpis.csv
-- Tableau : Bar chart with dual axis — avg_delivery_min + slow_order_pct
-- ================================================================

SELECT
    company,
    ROUND(AVG(delivery_time_min), 2)                           AS avg_delivery_min,
    ROUND(PERCENTILE_CONT(0.5)
          WITHIN GROUP (ORDER BY delivery_time_min::NUMERIC), 2) AS p50_delivery_min,
    ROUND(PERCENTILE_CONT(0.9)
          WITHIN GROUP (ORDER BY delivery_time_min::NUMERIC), 2) AS p90_delivery_min,
    COUNT(*) FILTER (WHERE delivery_time_min > 30)             AS slow_orders,
    ROUND(COUNT(*) FILTER (WHERE delivery_time_min > 30)
          * 100.0 / COUNT(*), 2)                               AS slow_order_pct
FROM qc_main
GROUP BY company
ORDER BY avg_delivery_min ASC;


-- ================================================================
-- QUERY 4: City-Level Revenue Breakdown
-- ================================================================
-- Metric  : Revenue, AOV, avg delivery per city per company
-- Filter  : Excludes 'Unknown' cities (data quality issue in raw data)
-- Export  : m1_city_revenue.csv
-- Tableau : Map or heat table — city on rows, company on columns,
--           revenue_millions on colour
-- ================================================================

SELECT
    company,
    city,
    COUNT(*)                                                   AS total_orders,
    ROUND(SUM(order_value) / 1000000.0, 2)                    AS revenue_millions,
    ROUND(AVG(order_value), 2)                                 AS avg_order_value,
    ROUND(AVG(delivery_time_min), 2)                           AS avg_delivery_min,
    ROUND(AVG(customer_rating), 2)                             AS avg_rating
FROM qc_main
WHERE city != 'Unknown'
GROUP BY company, city
ORDER BY company, revenue_millions DESC;


-- ================================================================
-- QUERY 5: Payment Method Distribution
-- ================================================================
-- Metric  : Order share by payment type per company
-- Window  : PARTITION BY company — % is calculated within each company
-- Export  : m1_payment_methods.csv
-- Tableau : 100% stacked bar — company on axis, payment_method as colour
-- ================================================================

SELECT
    company,
    payment_method,
    COUNT(*)                                                   AS orders,
    ROUND(COUNT(*) * 100.0 /
          SUM(COUNT(*)) OVER (PARTITION BY company), 2)       AS pct_of_company
FROM qc_main
GROUP BY company, payment_method
ORDER BY company, orders DESC;


-- ================================================================
-- QUERY 6: Order Value Tier Distribution
-- ================================================================
-- Metric  : Volume breakdown by Low/Medium/High/Premium order size
-- Note    : order_value_bucket is a derived column added during
--           data cleaning (CASE WHEN on order_value quartiles).
--           If this column is missing, run the ALTER TABLE fix in
--           python/00_data_cleaning.py first.
-- Export  : m1_order_value_tiers.csv
-- Tableau : Stacked bar chart — company vs orders, colour = bucket
-- ================================================================

SELECT
    company,
    order_value_bucket,
    COUNT(*)                                                   AS orders,
    ROUND(AVG(order_value), 2)                                 AS avg_order_value_in_bucket,
    ROUND(COUNT(*) * 100.0 /
          SUM(COUNT(*)) OVER (PARTITION BY company), 2)       AS pct_of_company
FROM qc_main
WHERE order_value_bucket IS NOT NULL
GROUP BY company, order_value_bucket
ORDER BY company, avg_order_value_in_bucket;


-- ================================================================
-- QUERY 7: Customer & Partner Ratings
-- ================================================================
-- Metric  : Avg ratings, % of orders rated 4 or above
-- Export  : m1_ratings.csv
-- Tableau : KPI scorecards or lollipop chart — one per company
-- ================================================================

SELECT
    company,
    ROUND(AVG(customer_rating), 3)                             AS avg_customer_rating,
    ROUND(AVG(delivery_partner_rating), 3)                     AS avg_partner_rating,
    COUNT(*) FILTER (WHERE customer_rating >= 4)               AS high_rated_orders,
    ROUND(COUNT(*) FILTER (WHERE customer_rating >= 4)
          * 100.0 / COUNT(*), 2)                               AS high_rating_pct
FROM qc_main
GROUP BY company
ORDER BY avg_customer_rating DESC;



