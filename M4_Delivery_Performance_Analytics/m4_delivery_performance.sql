-- ================================================================
-- Quick Commerce Wars
-- Module 4: Delivery Performance Analytics
-- ================================================================
-- Business question:
--   What factors drive delivery delays? Which companies, cities,
--   and partners underperform on speed?
--
-- ===================


-- ================================================================
-- STEP 0: Pre-flight check
-- ================================================================
-- Run this first. Confirm derived columns exist from cleaning.
-- If any return 0, run the ALTER TABLE fix in data/README.md.

SELECT
    COUNT(*) FILTER (WHERE delivery_speed_bucket IS NOT NULL) AS has_speed_bucket,
    COUNT(*) FILTER (WHERE distance_bucket IS NOT NULL)       AS has_dist_bucket,
    COUNT(*) FILTER (WHERE revenue_per_km IS NOT NULL)        AS has_rev_per_km
FROM qc_main;

-- Expected: all three columns = ~375,646 (no nulls)


-- ================================================================
-- QUERY 1: Company-Level Delivery Performance
-- ================================================================
-- Metric  : Avg delivery, P50, P90, efficiency ratio, slow rate.
--           This is the top-line KPI table for the dashboard.
-- ================================================================

SELECT
    company,
    COUNT(*)                                                   AS total_orders,
    ROUND(AVG(delivery_time_min), 2)                           AS avg_delivery_min,
    ROUND(PERCENTILE_CONT(0.5)
          WITHIN GROUP (ORDER BY delivery_time_min::NUMERIC), 2) AS p50_delivery_min,
    ROUND(PERCENTILE_CONT(0.9)
          WITHIN GROUP (ORDER BY delivery_time_min::NUMERIC), 2) AS p90_delivery_min,
    ROUND(AVG(distance_km), 2)                                 AS avg_distance_km,
    ROUND(AVG(distance_km / NULLIF(delivery_time_min, 0)), 4)  AS avg_efficiency_ratio,
    COUNT(*) FILTER (WHERE delivery_time_min > 30)             AS slow_orders,
    ROUND(COUNT(*) FILTER (WHERE delivery_time_min > 30)
          * 100.0 / COUNT(*), 2)                               AS slow_order_pct
FROM qc_main
GROUP BY company
ORDER BY avg_efficiency_ratio DESC;


-- ================================================================
-- QUERY 2: City × Company Performance Heatmap
-- ================================================================
-- Metric  : Avg delivery, slow rate, and efficiency per city
--           per company. Feeds the city heatmap in Tableau.
===============================

SELECT
    company,
    city,
    COUNT(*)                                                   AS total_orders,
    ROUND(AVG(delivery_time_min), 2)                           AS avg_delivery_min,
    ROUND(PERCENTILE_CONT(0.9)
          WITHIN GROUP (ORDER BY delivery_time_min::NUMERIC), 2) AS p90_delivery_min,
    ROUND(AVG(distance_km / NULLIF(delivery_time_min, 0)), 4)  AS avg_efficiency_ratio,
    COUNT(*) FILTER (WHERE delivery_time_min > 30)             AS slow_orders,
    ROUND(COUNT(*) FILTER (WHERE delivery_time_min > 30)
          * 100.0 / COUNT(*), 2)                               AS slow_order_pct
FROM qc_main
WHERE city != 'Unknown'
GROUP BY company, city
ORDER BY slow_order_pct DESC;


-- ================================================================
-- QUERY 3: Delivery Speed Bucket Distribution
-- ================================================================
-- Metric  : % of orders in each speed bucket per company.
--           Express (<10 min), Fast (10-20), Standard (20-30),
--           Slow (>30 min).
-- ================================================================

SELECT
    company,
    delivery_speed_bucket,
    COUNT(*)                                                   AS orders,
    ROUND(COUNT(*) * 100.0 /
          SUM(COUNT(*)) OVER (PARTITION BY company), 2)       AS pct_of_company
FROM qc_main
WHERE delivery_speed_bucket IS NOT NULL
GROUP BY company, delivery_speed_bucket
ORDER BY company, pct_of_company DESC;


-- ================================================================
-- QUERY 4: Delivery Partner Tier Performance
-- ================================================================
-- Metric  : Delivery time and efficiency by partner rating tier.
--           Validates that partner rating is a real signal, not
--           just customer perception.
-- ================================================================

SELECT
    company,
    CASE
        WHEN delivery_partner_rating >= 4.5 THEN '1. Elite (4.5+)'
        WHEN delivery_partner_rating >= 4.0 THEN '2. Good (4.0-4.5)'
        WHEN delivery_partner_rating >= 3.0 THEN '3. Average (3.0-4.0)'
        ELSE                                    '4. Poor (<3.0)'
    END                                                        AS partner_tier,
    COUNT(*)                                                   AS orders,
    ROUND(AVG(delivery_time_min), 2)                           AS avg_delivery_min,
    ROUND(AVG(distance_km / NULLIF(delivery_time_min, 0)), 4)  AS avg_efficiency_ratio,
    ROUND(AVG(customer_rating), 3)                             AS avg_customer_rating
FROM qc_main
GROUP BY company,
    CASE
        WHEN delivery_partner_rating >= 4.5 THEN '1. Elite (4.5+)'
        WHEN delivery_partner_rating >= 4.0 THEN '2. Good (4.0-4.5)'
        WHEN delivery_partner_rating >= 3.0 THEN '3. Average (3.0-4.0)'
        ELSE                                    '4. Poor (<3.0)'
    END
ORDER BY company, partner_tier;


-- ================================================================
-- QUERY 5: Distance Bucket vs Delivery Time
-- ================================================================
-- Metric  : Avg delivery time broken down by distance bucket.
--           Shows the relationship between distance and time.
--
-- ================================================================

SELECT
    company,
    distance_bucket,
    COUNT(*)                                                   AS orders,
    ROUND(AVG(delivery_time_min), 2)                           AS avg_delivery_min,
    ROUND(AVG(distance_km), 2)                                 AS avg_distance_km,
    ROUND(AVG(distance_km / NULLIF(delivery_time_min, 0)), 4)  AS avg_efficiency_ratio
FROM qc_main
WHERE distance_bucket IS NOT NULL
GROUP BY company, distance_bucket
ORDER BY company, avg_distance_km;


-- ================================================================
-- QUERY 6: Outlier Cities — Highest Slow Order Rates
-- ================================================================
-- Metric  : Cities where slow order rate (>30 min) is highest.
--           Surfaces operational problem areas per company.
--
-- ================================================================

SELECT
    company,
    city,
    COUNT(*)                                                   AS total_orders,
    COUNT(*) FILTER (WHERE delivery_time_min > 30)             AS slow_orders,
    ROUND(COUNT(*) FILTER (WHERE delivery_time_min > 30)
          * 100.0 / COUNT(*), 2)                               AS slow_order_pct,
    ROUND(AVG(delivery_time_min), 2)                           AS avg_delivery_min
FROM qc_main
WHERE city != 'Unknown'
GROUP BY company, city
HAVING COUNT(*) >= 100
ORDER BY slow_order_pct DESC
LIMIT 20;


-- ================================================================
-- QUERY 7: City Rankings — P90 and Efficiency (dual RANK)
-- ================================================================
-- Metric  : Each city ranked by both P90 delivery time and
--           efficiency ratio within its company.
--
-- ================================================================

WITH city_metrics AS (
    SELECT
        company,
        city,
        COUNT(*)                                                 AS total_orders,
        ROUND(AVG(delivery_time_min), 2)                         AS avg_delivery_min,
        ROUND(PERCENTILE_CONT(0.9)
              WITHIN GROUP (ORDER BY delivery_time_min::NUMERIC), 2) AS p90_delivery_min,
        ROUND(AVG(distance_km / NULLIF(delivery_time_min, 0)), 4)    AS avg_efficiency_ratio
    FROM qc_main
    WHERE city != 'Unknown'
    GROUP BY company, city
    HAVING COUNT(*) >= 100
)
SELECT
    company,
    city,
    total_orders,
    avg_delivery_min,
    p90_delivery_min,
    avg_efficiency_ratio,
    RANK() OVER (
        PARTITION BY company
        ORDER BY p90_delivery_min DESC
    )                                                            AS rank_p90_worst,
    RANK() OVER (
        PARTITION BY company
        ORDER BY avg_efficiency_ratio ASC
    )                                                            AS rank_efficiency_worst
FROM city_metrics
ORDER BY company, rank_p90_worst;


