# Quick-Commerce-Wars

**What This Project Is**:

A 7-module end-to-end analytics study comparing India's three largest quick commerce platforms across market share, dark store expansion, customer retention, delivery efficiency, customer segmentation, product mix, and unit economics.

Dataset: ~375K orders, 100K delivery records, 4K dark store locations, India census demographics.

Stack: PostgreSQL for aggregations and window functions · Python (Google Colab) for data cleaning, machine learning, and simulations · Tableau Public for dashboards.

Repository Structure

quick-commerce-wars/
│
├── README.md                        ← You are here
├── .gitignore
│
├── sql/
│   ├── m1_executive_kpis.sql        ← Market share, revenue, delivery, ratings
│   ├── m2_dark_store_expansion.sql
│   ├── m3_customer_retention.sql
│   ├── m4_delivery_performance.sql
│   ├── m5_segmentation_queries.sql
│   ├── m6_category_analytics.sql
│   └── m7_profitability_base.sql
│
├── python/
│   ├── 00_data_cleaning.py          ← Run first — cleans all 4 raw CSVs
│   ├── m1_executive_kpis.py         ← Verification + summary output
│   ├── m2_expansion_scoring.py      ← Opportunity score, composite priority
│   ├── m3_retention_analysis.py     ← Cross-dataset retention metrics
│   ├── m4_delivery_correlation.py   ← Pearson correlation, outlier detection
│   ├── m5_kmeans_segmentation.py    ← Elbow, silhouette, K-Means, PCA
│   ├── m6_category_scorecard.py     ← Revenue vs risk cross-dataset join
│   └── m7_profitability_sim.py      ← Margin model, scenarios, heatmap
│
└── data/
    └── README.md                    ← Schema reference (raw files not committed)
