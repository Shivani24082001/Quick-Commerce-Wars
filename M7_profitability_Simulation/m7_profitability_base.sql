-- ================================================================
-- Quick Commerce Wars
-- Module 7: Profitability Simulation
-- ================================================================
-- ================================================================


-- ================================================================
-- QUERY 1: Revenue Baseline per Company
-- ================================================================
-- Purpose : The single most important SQL query in M7.
--           Gives Python the exact revenue, distance, discount rate,
--           and AOV numbers per company to seed the simulation.
-- ================================================================

SELECT
    company,
    COUNT(*)                                                 AS total_orders,
    ROUND(SUM(order_value) / 1000000.0, 2)                  AS total_revenue_m,
    ROUND(AVG(order_value), 2)                               AS avg_order_value,
    ROUND(AVG(distance_km), 2)                               AS avg_distance_km,
    ROUND(AVG(is_discounted) * 100, 2)                       AS discount_rate_pct,
    ROUND(AVG(order_value)
          FILTER (WHERE is_discounted = 1), 2)               AS disc_aov,
    ROUND(AVG(order_value)
          FILTER (WHERE is_discounted = 0), 2)               AS full_aov,
    ROUND(SUM(distance_km), 2)                               AS total_distance_km
FROM qc_main
GROUP BY company
ORDER BY total_revenue_m DESC;


-- ================================================================
-- QUERY 2: Order Value Distribution by Bucket
-- ================================================================
-- Purpose : Shows what % of orders fall in each value tier.
--           Python uses this distribution to model how scenarios
--           (e.g. +15% AOV) shift orders across tiers and
--           their impact on total margin.
-- ================================================================

SELECT
    company,
    order_value_bucket,
    COUNT(*)                                                  AS orders,
    ROUND(COUNT(*) * 100.0 /
          SUM(COUNT(*)) OVER (PARTITION BY company), 2)      AS pct_of_company,
    ROUND(AVG(order_value), 2)                                AS avg_order_value,
    ROUND(AVG(distance_km), 2)                                AS avg_distance_km,
    ROUND(AVG(is_discounted) * 100, 2)                        AS discount_rate_pct
FROM qc_main
WHERE order_value_bucket IS NOT NULL
GROUP BY company, order_value_bucket
ORDER BY company, avg_order_value;


-- ================================================================
-- QUERY 3: Discounted vs Full-Price Order Profile
-- ================================================================
-- Purpose : Quantifies how different discounted orders are from
--           full-price orders — AOV, distance, and volume.
--           This is the key input for the "cut discounts" scenario.
--           If disc_aov is much higher than full_aov, cutting
--           discounts removes your highest-value orders alongside
--           the cost — a trap the simulation makes visible.
-- ================================================================

SELECT
    company,
    is_discounted,
    COUNT(*)                                                  AS orders,
    ROUND(COUNT(*) * 100.0 /
          SUM(COUNT(*)) OVER (PARTITION BY company), 2)      AS pct_of_company,
    ROUND(AVG(order_value), 2)                                AS avg_order_value,
    ROUND(AVG(distance_km), 2)                                AS avg_distance_km,
    ROUND(SUM(order_value) / 1000000.0, 2)                   AS revenue_millions
FROM qc_main
GROUP BY company, is_discounted
ORDER BY company, is_discounted;


-- ================================================================
-- QUERY 4: Category-Level Revenue and Distance
-- ================================================================
-- Purpose : Enables the Python simulation to run at category level
--           as well as company level. Useful for identifying which
--           category should be prioritised for discount reduction
--           (combine with M6 discount lift data).
=======

SELECT
    company,
    product_category,
    COUNT(*)                                                  AS orders,
    ROUND(SUM(order_value) / 1000000.0, 3)                   AS revenue_millions,
    ROUND(AVG(order_value), 2)                                AS avg_order_value,
    ROUND(AVG(distance_km), 2)                                AS avg_distance_km,
    ROUND(AVG(is_discounted) * 100, 2)                        AS discount_rate_pct,
    ROUND(AVG(order_value)
          FILTER (WHERE is_discounted = 1), 2)                AS disc_aov,
    ROUND(AVG(order_value)
          FILTER (WHERE is_discounted = 0), 2)                AS full_aov
FROM qc_main
WHERE product_category IS NOT NULL
GROUP BY company, product_category
ORDER BY company, revenue_millions DESC;


