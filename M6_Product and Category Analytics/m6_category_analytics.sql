-- ================================================================
-- Quick Commerce Wars
-- Module 6: Product & Category Analytics
-- ================================================================
-- ================================================================
-- STEP 0: Pre-flight checks
-- ================================================================

-- Confirm categories and row counts
SELECT
    product_category,
    COUNT(*)                        AS total_orders,
    ROUND(AVG(order_value), 2)      AS avg_order_value
FROM qc_main
WHERE product_category IS NOT NULL
GROUP BY product_category
ORDER BY total_orders DESC;

-- Check items_count nulls (needed for basket analysis in Query 5)
SELECT
    COUNT(*) FILTER (WHERE items_count IS NULL) AS null_item_count,
    COUNT(*)                                    AS total_rows
FROM qc_main;
-- If null_item_count > 0, the HAVING clause in Query 5 filters them out.


-- ================================================================
-- QUERY 1: Category Revenue Summary (overall, all companies)
-- ================================================================
-- Metric  : Total revenue, AOV, order count per category.
--           The headline ranking — which categories earn the most.
-- ================================================================

SELECT
    product_category,
    COUNT(*)                                              AS total_orders,
    ROUND(SUM(order_value) / 1000000.0, 2)               AS revenue_millions,
    ROUND(AVG(order_value), 2)                            AS avg_order_value,
    ROUND(AVG(customer_rating), 3)                        AS avg_rating,
    ROUND(AVG(is_discounted) * 100, 2)                    AS discount_rate_pct,
    ROUND(AVG(items_count), 2)                            AS avg_items_per_order
FROM qc_main
WHERE product_category IS NOT NULL
GROUP BY product_category
ORDER BY revenue_millions DESC;


-- ================================================================
-- QUERY 2: Category × Company Breakdown
-- ================================================================
-- Metric  : Revenue and AOV per category per company.
--           Shows which company dominates each category
--           and where there are competitive gaps.
-- ================================================================

SELECT
    product_category,
    company,
    COUNT(*)                                               AS total_orders,
    ROUND(SUM(order_value) / 1000000.0, 2)                AS revenue_millions,
    ROUND(AVG(order_value), 2)                             AS avg_order_value,
    ROUND(AVG(customer_rating), 3)                         AS avg_rating,
    ROUND(AVG(is_discounted) * 100, 2)                     AS discount_rate_pct,
    ROUND(COUNT(*) * 100.0 /
          SUM(COUNT(*)) OVER (PARTITION BY product_category), 2) AS share_within_category
FROM qc_main
WHERE product_category IS NOT NULL
GROUP BY product_category, company
ORDER BY product_category, revenue_millions DESC;


-- ================================================================
-- QUERY 3: Discount Dependency & Lift per Category
-- ================================================================
-- Metric  : For each category — discount rate, AOV with discount,
--           AOV without discount, and LIFT %.
--
-- Discount Lift = (disc_aov - full_aov) / full_aov × 100
--
-- Interpretation:
--   High lift (>40%): discounts attract genuinely bigger baskets
--                     — discounting is driving volume, not just
--                     reducing margin on existing orders.
--   Low lift (<10%): discounts are not growing baskets — they are
--                    just giving money away. Cut them here first.
-- ================================================================

SELECT
    product_category,
    COUNT(*)                                                AS total_orders,
    ROUND(AVG(is_discounted) * 100, 2)                      AS discount_rate_pct,
    ROUND(AVG(order_value)
          FILTER (WHERE is_discounted = 1), 2)              AS disc_aov,
    ROUND(AVG(order_value)
          FILTER (WHERE is_discounted = 0), 2)              AS full_aov,
    ROUND(
        (AVG(order_value) FILTER (WHERE is_discounted = 1) -
         AVG(order_value) FILTER (WHERE is_discounted = 0))
        / NULLIF(AVG(order_value) FILTER (WHERE is_discounted = 0), 0)
        * 100
    , 2)                                                    AS discount_lift_pct
FROM qc_main
WHERE product_category IS NOT NULL
GROUP BY product_category
ORDER BY discount_lift_pct DESC;


-- ================================================================
-- QUERY 4: Category × Company Ratings Heatmap
-- ================================================================
-- Metric  : Avg customer rating per category per company.
--           Shows which company delivers the best customer
--           experience in each category.
-- ================================================================

SELECT
    product_category,
    company,
    COUNT(*)                                               AS orders,
    ROUND(AVG(customer_rating), 3)                         AS avg_customer_rating,
    ROUND(AVG(delivery_partner_rating), 3)                 AS avg_partner_rating,
    COUNT(*) FILTER (WHERE customer_rating >= 4)           AS high_rated_orders,
    ROUND(COUNT(*) FILTER (WHERE customer_rating >= 4)
          * 100.0 / COUNT(*), 2)                           AS high_rating_pct
FROM qc_main
WHERE product_category IS NOT NULL
GROUP BY product_category, company
ORDER BY product_category, avg_customer_rating DESC;


-- ================================================================
-- QUERY 5: Basket Size Analysis (items per order)
-- ================================================================
-- Metric  : Average items per order and AOV per items bucket
--           broken down by category and company.
-- ================================================================

WITH basket_data AS (
    SELECT
        product_category,
        company,
        order_value,
        items_count,
        CASE
            WHEN items_count = 1  THEN '1 item'
            WHEN items_count <= 3 THEN '2-3 items'
            WHEN items_count <= 5 THEN '4-5 items'
            ELSE                       '6+ items'
        END AS basket_size_bucket
    FROM qc_main
    WHERE product_category IS NOT NULL
      AND items_count IS NOT NULL
)
SELECT
    product_category,
    company,
    basket_size_bucket,
    COUNT(*)                           AS orders,
    ROUND(AVG(order_value), 2)         AS avg_order_value,
    ROUND(AVG(items_count), 2)         AS avg_items
FROM basket_data
GROUP BY product_category, company, basket_size_bucket
ORDER BY product_category, company, avg_items;


-- ================================================================
-- QUERY 6: Category Scorecard (SQL summary table)
-- ================================================================
-- Metric  : One row per category combining revenue, rating,
--           discount dependency, and basket size into a single
--           view. This is the SQL-only scorecard — the Python
--           version adds refund data from ecommerce_analytics.
-- ================================================================

SELECT
    product_category,
    COUNT(*)                                               AS total_orders,
    ROUND(SUM(order_value) / 1000000.0, 2)                AS revenue_millions,
    ROUND(AVG(order_value), 2)                             AS avg_order_value,
    ROUND(AVG(customer_rating), 3)                         AS avg_rating,
    ROUND(AVG(is_discounted) * 100, 2)                     AS discount_rate_pct,
    ROUND(AVG(items_count), 2)                             AS avg_basket_size,
    -- Discount lift inline
    ROUND(
        (AVG(order_value) FILTER (WHERE is_discounted = 1) -
         AVG(order_value) FILTER (WHERE is_discounted = 0))
        / NULLIF(AVG(order_value) FILTER (WHERE is_discounted = 0), 0)
        * 100
    , 2)                                                   AS discount_lift_pct,
    -- High performer flag: above-average rating AND above-average revenue
    CASE
        WHEN AVG(customer_rating) >= 3.5
         AND SUM(order_value) / 1000000.0 >= 
             (SELECT AVG(rev) FROM (
                 SELECT SUM(order_value) / 1000000.0 AS rev
                 FROM qc_main
                 GROUP BY product_category
             ) sub)
        THEN 'Star'
        WHEN AVG(customer_rating) < 3.2 THEN 'Needs Attention'
        ELSE 'Average'
    END                                                    AS category_status
FROM qc_main
WHERE product_category IS NOT NULL
GROUP BY product_category
ORDER BY revenue_millions DESC;


-- ================================================================
