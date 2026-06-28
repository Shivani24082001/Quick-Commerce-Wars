Business Question

What distinct customer behaviour patterns exist across the three platforms — and how should each segment be targeted differently?

Why K-Means Instead of RFM

RFM (Recency/Frequency/Monetary) is the standard customer segmentation framework. It was not possible here because:


No customer IDs in qc_main — you cannot aggregate orders by customer without an identifier
Corrupted timestamps in ecommerce_analytics — the date column was dropped during cleaning


K-Means on order-level features produces equivalent business segments. Instead of tracking a customer's recency and frequency across time, we cluster individual orders by spending level, satisfaction, price sensitivity, and delivery experience. The four resulting segments — Champions, Loyals, Price-Sensitive, At-Risk — map to the same strategic categories an RFM analysis would produce.


Why StandardScaler Is Mandatory

K-Means computes distances between data points. Without scaling, order_value (values in hundreds of rupees) completely dominates the distance calculation over customer_rating (scale 1–5). A ₹500 difference looks far more significant than a 2-star rating difference, even if both are equally important for segmentation.

After StandardScaler, every feature has mean=0 and std=1. A 1-unit difference in order_value carries exactly the same weight as a 1-unit difference in customer_rating. Clusters reflect relative behaviour patterns rather than the arbitrary units each feature happens to use.


How to Choose k

Elbow method — Plot inertia (within-cluster sum of squares) against k. Inertia drops sharply then levels off. The "elbow" is where additional clusters stop providing meaningful separation.

Silhouette score — Computed on a 10K sample. Measures how well each point fits its own cluster vs the nearest alternative. Score > 0.2 is acceptable for real-world behavioural data.

Both methods are applied in Cells 3 and 4. The final choice of k=4 is supported by both the statistical results and business interpretability — four segments (Champions, Loyals, Price-Sensitive, At-Risk) have clear strategic meaning.
