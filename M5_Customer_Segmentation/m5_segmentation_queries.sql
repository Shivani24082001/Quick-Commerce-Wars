-- ================================================================
-- Quick Commerce Wars
-- Module 5: Customer Segmentation (K-Means)
-- ================================================================
-- ================================================================
-- ================================================================
-- ================================================================

SELECT
    order_id,
    company,
    city,
    order_value,
    customer_rating,
    is_discounted,
    distance_km,
    delivery_time_min,
    customer_age,
    product_category,
    payment_method
FROM qc_main
WHERE
    order_value       IS NOT NULL
    AND customer_rating    IS NOT NULL
    AND distance_km        IS NOT NULL
    AND delivery_time_min  IS NOT NULL
    AND customer_age       IS NOT NULL
ORDER BY order_id;

-- Expected: ~375,000 rows (near-complete — nulls were filled in cleaning)


-- ================================================================
-- QUERY 2: Post-Clustering — Segment Distribution per Company
-- ================================================================
-- ================================================================

-- Step A: Create the table (run once after Python saves the CSV)
-- CREATE TABLE IF NOT EXISTS m5_clusters (
--     order_id       BIGINT,
--     company        VARCHAR(50),
--     city           VARCHAR(50),
--     cluster        INT,
--     segment_label  VARCHAR(30)
-- );
-- Then import m5_clustered_orders.csv via pgAdmin Import/Export.

-- Step B: Segment distribution query (run after import)
-- Export as: m5_segment_distribution.csv
-- Tableau  : 100% stacked bar — company on X, segment as colour

SELECT
    company,
    segment_label,
    COUNT(*)                                                   AS orders,
    ROUND(COUNT(*) * 100.0 /
          SUM(COUNT(*)) OVER (PARTITION BY company), 2)       AS pct_of_company
FROM m5_clusters
GROUP BY company, segment_label
ORDER BY company, orders DESC;

