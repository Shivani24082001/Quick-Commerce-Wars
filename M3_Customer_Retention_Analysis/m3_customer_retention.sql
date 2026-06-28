-- ================================================================
-- Quick Commerce Wars
-- Module 3: Customer Retention Analysis
-- ================================================================
--
-- Business question:
--   What drives customers to churn? Is it refunds, delays,
--   low ratings — or a combination? Which categories have
--   the worst retention profile?
--
--
-- Note on methodology:
--   Monthly cohort analysis is NOT possible in this dataset.
--   The 'Order Date & Time' column was corrupted in the raw data
--   and was dropped during cleaning. Customer segmentation is
--   therefore based on order_frequency + service_rating rather
--   than recency/frequency/monetary (RFM).
-- ================================================================


-- ================================================================
-- STEP 0: Table setup (run once)
-- ================================================================

CREATE TABLE IF NOT EXISTS ecommerce_analytics (
    order_id          VARCHAR(20) PRIMARY KEY,
    order_index       INT,
    customer_id       VARCHAR(20),
    company           VARCHAR(50),
    delivery_time_min INT,
    product_category  VARCHAR(50),
    order_value       INT,
    customer_feedback TEXT,
    service_rating    INT,
    had_delay         INT,       -- 1 = delivery was delayed
    had_refund        INT,       -- 1 = refund was requested
    is_satisfied      INT,       -- 1 = service_rating >= 4
    is_at_risk        INT,       -- 1 = low frequency + bad experience
    order_value_bucket VARCHAR(20),
    order_frequency   INT,
    refund_rate       NUMERIC(6,4)
);

-- Import ecommerce_analytics_cleaned.csv via pgAdmin Import/Export


-- ================================================================
-- STEP 1: Sanity check
-- ================================================================

SELECT
    company,
    COUNT(*)                        AS total_records,
    ROUND(AVG(service_rating), 2)   AS avg_rating,
    SUM(had_refund)                 AS total_refunds,
    SUM(had_delay)                  AS total_delays
FROM ecommerce_analytics
GROUP BY company
ORDER BY total_records DESC;


-- ================================================================
-- QUERY 1: Repeat Order Rate by Company
-- ================================================================
-- Metric  : What % of customers ordered more than once?
--           order_frequency > 1 = repeat customer.
-- ================================================================

SELECT
    company,
    COUNT(*)                                               AS total_records,
    COUNT(*) FILTER (WHERE order_frequency > 1)            AS repeat_customers,
    ROUND(COUNT(*) FILTER (WHERE order_frequency > 1)
          * 100.0 / COUNT(*), 2)                           AS repeat_rate_pct,
    ROUND(AVG(order_frequency), 2)                         AS avg_order_frequency
FROM ecommerce_analytics
GROUP BY company
ORDER BY repeat_rate_pct DESC;


-- ================================================================
-- QUERY 2: Customer Segments by Order Frequency + Rating
-- ================================================================
-- Metric  : Segment every record into one of 4 buckets based on
--           their order frequency and service rating.
-- ================================================================

SELECT
    company,
    CASE
        WHEN order_frequency >= 5 AND service_rating >= 4  THEN 'Champions'
        WHEN order_frequency >= 3 AND service_rating >= 3  THEN 'Loyals'
        WHEN order_frequency >= 2 AND service_rating < 3   THEN 'At-Risk'
        ELSE                                                    'Occasional'
    END                                                    AS segment,
    COUNT(*)                                               AS customers,
    ROUND(AVG(order_frequency), 2)                         AS avg_frequency,
    ROUND(AVG(service_rating), 2)                          AS avg_rating,
    ROUND(COUNT(*) * 100.0 /
          SUM(COUNT(*)) OVER (PARTITION BY company), 2)    AS pct_of_company
FROM ecommerce_analytics
GROUP BY company,
    CASE
        WHEN order_frequency >= 5 AND service_rating >= 4  THEN 'Champions'
        WHEN order_frequency >= 3 AND service_rating >= 3  THEN 'Loyals'
        WHEN order_frequency >= 2 AND service_rating < 3   THEN 'At-Risk'
        ELSE                                                    'Occasional'
    END
ORDER BY company, customers DESC;


-- ================================================================
-- QUERY 3: Refund Impact on Order Frequency
-- ================================================================
-- Metric  : Do customers who requested a refund order less often?
--           Compare avg order_frequency for had_refund=1 vs 0.
-- ================================================================

SELECT
    company,
    had_refund,
    COUNT(*)                               AS customers,
    ROUND(AVG(order_frequency), 2)         AS avg_order_frequency,
    ROUND(AVG(service_rating), 2)          AS avg_service_rating,
    ROUND(AVG(order_value), 2)             AS avg_order_value
FROM ecommerce_analytics
GROUP BY company, had_refund
ORDER BY company, had_refund;


-- ================================================================
-- QUERY 4: Delay Impact on Order Frequency
-- ================================================================
-- Metric  : Do delayed orders drive lower repeat rates or ratings?
-- ================================================================

SELECT
    company,
    had_delay,
    COUNT(*)                               AS customers,
    ROUND(AVG(order_frequency), 2)         AS avg_order_frequency,
    ROUND(AVG(service_rating), 2)          AS avg_service_rating
FROM ecommerce_analytics
GROUP BY company, had_delay
ORDER BY company, had_delay;


-- ================================================================
-- QUERY 5: Rating Distribution by Company
-- ================================================================
-- Metric  : How are service ratings spread across 1–5 for each
--           company? What % of orders are rated 4 or above?
-- ================================================================

SELECT
    company,
    service_rating                         AS rating,
    COUNT(*)                               AS customers,
    ROUND(AVG(order_frequency), 2)         AS avg_order_frequency,
    ROUND(COUNT(*) * 100.0 /
          SUM(COUNT(*)) OVER (PARTITION BY company), 2) AS pct_of_company
FROM ecommerce_analytics
GROUP BY company, service_rating
ORDER BY company, service_rating;


-- ================================================================
-- QUERY 6: At-Risk Customer Rate per Company
-- ================================================================
-- Metric  : % of customers who are "at-risk" — defined as
--           low order frequency AND a bad experience (refund or delay).
-- ================================================================

SELECT
    company,
    COUNT(*)                                                       AS total_customers,
    COUNT(*) FILTER (WHERE is_at_risk = 1)                         AS at_risk_customers,
    ROUND(COUNT(*) FILTER (WHERE is_at_risk = 1)
          * 100.0 / COUNT(*), 2)                                   AS at_risk_rate_pct,
    -- Breakdown of what triggered the at-risk flag
    COUNT(*) FILTER (WHERE is_at_risk = 1 AND had_refund = 1)      AS at_risk_from_refund,
    COUNT(*) FILTER (WHERE is_at_risk = 1 AND had_delay  = 1)      AS at_risk_from_delay
FROM ecommerce_analytics
GROUP BY company
ORDER BY at_risk_rate_pct DESC;


-- ================================================================
-- QUERY 7: Category-Level Refund Rates
-- ================================================================
-- Metric  : Which product categories have the highest refund rates?
--           Perishables (Fruits & Veg, Dairy) typically rank highest
--           because product quality on delivery is harder to guarantee.
-- ================================================================

SELECT
    product_category,
    COUNT(*)                                AS records,
    ROUND(AVG(refund_rate) * 100, 2)        AS avg_refund_rate_pct,
    ROUND(AVG(service_rating), 2)           AS avg_service_rating,
    ROUND(AVG(order_frequency), 2)          AS avg_order_frequency,
    SUM(had_refund)                         AS total_refunds
FROM ecommerce_analytics
GROUP BY product_category
ORDER BY avg_refund_rate_pct DESC;


-- ================================================================
-- QUERY 8: Refund + Delay Combined Impact
-- ================================================================
-- Metric  : What happens to ratings and frequency when a customer
--           had BOTH a refund AND a delay in the same order?
--           This is the worst-case experience bucket.
-- ================================================================

SELECT
    CASE
        WHEN had_refund = 0 AND had_delay = 0 THEN '1. Neither'
        WHEN had_refund = 0 AND had_delay = 1 THEN '2. Delay Only'
        WHEN had_refund = 1 AND had_delay = 0 THEN '3. Refund Only'
        ELSE                                       '4. Both'
    END                                         AS experience_type,
    COUNT(*)                                    AS customers,
    ROUND(AVG(order_frequency), 2)              AS avg_order_frequency,
    ROUND(AVG(service_rating), 2)               AS avg_service_rating,
    ROUND(AVG(order_value), 2)                  AS avg_order_value
FROM ecommerce_analytics
GROUP BY
    CASE
        WHEN had_refund = 0 AND had_delay = 0 THEN '1. Neither'
        WHEN had_refund = 0 AND had_delay = 1 THEN '2. Delay Only'
        WHEN had_refund = 1 AND had_delay = 0 THEN '3. Refund Only'
        ELSE                                       '4. Both'
    END
ORDER BY experience_type;


