# ================================================================
# Quick Commerce Wars
# Module 3: Customer Retention Analysis — Python Script
# ================================================================
#
 ================================================================

import pandas as pd
import numpy as np
import os
import warnings
warnings.filterwarnings('ignore')


# ================================================================
# CELL 1: Load both datasets
# ================================================================

qc = pd.read_csv(f"{CLEAN}/qc_main_cleaned.csv")
ea = pd.read_csv(f"{CLEAN}/ecommerce_analytics_cleaned.csv")

print("=== DATA LOADED ===")
print(f"qc_main              : {qc.shape}")
print(f"ecommerce_analytics  : {ea.shape}")

# Align column names for the join
# Both datasets have 'company' and 'product_category'
print(f"\nqc_main categories      : {sorted(qc['product_category'].unique())}")
print(f"ecommerce categories    : {sorted(ea['product_category'].unique())}")

# Check category names match exactly (they must for the join to work)
qc_cats = set(qc['product_category'].dropna().unique())
ea_cats  = set(ea['product_category'].dropna().unique())
common   = qc_cats & ea_cats
qc_only  = qc_cats - ea_cats
ea_only  = ea_cats - qc_cats

print(f"\nCategories in both     : {sorted(common)}")
if qc_only:
    print(f"Categories in qc only  : {sorted(qc_only)}")
if ea_only:
    print(f"Categories in ea only  : {sorted(ea_only)}")


# ================================================================
# CELL 2: Category × Platform cross view
# ================================================================
print("\n=== BUILDING CATEGORY × PLATFORM VIEW ===")

# Side A — revenue and order metrics from qc_main
qc_agg = qc.groupby(['product_category', 'company']).agg(
    total_orders    = ('order_id',            'count'),
    revenue_millions= ('order_value',          lambda x: round(x.sum() / 1_000_000, 2)),
    avg_order_value = ('order_value',          lambda x: round(x.mean(), 2)),
    avg_rating      = ('customer_rating',      lambda x: round(x.mean(), 3)),
    discount_rate   = ('is_discounted',        lambda x: round(x.mean() * 100, 2)),
).reset_index()

# Side B — retention and refund metrics from ecommerce_analytics
ea_agg = ea.groupby(['product_category', 'company']).agg(
    avg_refund_rate  = ('refund_rate',      lambda x: round(x.mean() * 100, 2)),
    avg_satisfaction = ('is_satisfied',     lambda x: round(x.mean() * 100, 2)),
    avg_frequency    = ('order_frequency',  lambda x: round(x.mean(), 2)),
    at_risk_pct      = ('is_at_risk',       lambda x: round(x.mean() * 100, 2)),
).reset_index()

# Join on category + company
cat_platform = qc_agg.merge(
    ea_agg,
    on=['product_category', 'company'],
    how='left'
)

# Fill unmatched with 0 (shouldn't happen if category names are aligned)
fill_cols = ['avg_refund_rate', 'avg_satisfaction', 'avg_frequency', 'at_risk_pct']
cat_platform[fill_cols] = cat_platform[fill_cols].fillna(0)

print(cat_platform.sort_values(['product_category', 'company'])
      .to_string(index=False))

outpath = f"{OUTDIR}/m3_category_platform.csv"
cat_platform.to_csv(outpath, index=False)
print(f"\nSaved ({len(cat_platform)} rows) → {outpath}")
print("Tableau: Use this for the Category × Company heatmap")
print("         Colour by avg_refund_rate, size by revenue_millions")


# ================================================================
# CELL 3: Value-tier retention analysis
# ================================================================

print("\n=== VALUE TIER RETENTION ANALYSIS ===")

# qc_main — avg order value and rating per bucket
qc_bucket = qc.groupby(['company', 'order_value_bucket']).agg(
    total_orders    = ('order_id',         'count'),
    avg_order_value = ('order_value',       lambda x: round(x.mean(), 2)),
    avg_rating      = ('customer_rating',   lambda x: round(x.mean(), 3)),
    discount_rate   = ('is_discounted',     lambda x: round(x.mean() * 100, 2)),
).reset_index()

# ecommerce_analytics — refund rate per company
ea_company = ea.groupby('company').agg(
    avg_refund_rate = ('refund_rate',     lambda x: round(x.mean() * 100, 2)),
    avg_at_risk_pct = ('is_at_risk',      lambda x: round(x.mean() * 100, 2)),
    avg_frequency   = ('order_frequency', lambda x: round(x.mean(), 2)),
).reset_index()

# Join on company (ea doesn't have order_value_bucket — it's a
# company-level join, not bucket-level)
value_retention = qc_bucket.merge(ea_company, on='company', how='left')

# Bucket sort order for cleaner Tableau display
bucket_order = {
    'Budget (<₹200)'    : 1,
    'Mid (₹200-500)'    : 2,
    'Premium (₹500-1k)' : 3,
    'High-Value (>₹1k)' : 4,
}
value_retention['bucket_order'] = (
    value_retention['order_value_bucket'].map(bucket_order).fillna(5)
)
value_retention = value_retention.sort_values(
    ['company', 'bucket_order']
).drop(columns='bucket_order')

print(value_retention.to_string(index=False))

outpath = f"{OUTDIR}/m3_value_retention.csv"
value_retention.to_csv(outpath, index=False)
print(f"\nSaved ({len(value_retention)} rows) → {outpath}")
print("Tableau: Use for value tier analysis — bucket on X, avg_rating on Y")


# ================================================================
# CELL 4: Output checklist
# ================================================================

SQL_FILES = [
    ("m3_repeat_rate.csv",           "3 rows",   "SQL Query 1"),
    ("m3_segments.csv",              "~12 rows", "SQL Query 2"),
    ("m3_refund_impact.csv",         "~6 rows",  "SQL Query 3"),
    ("m3_delay_impact.csv",          "~6 rows",  "SQL Query 4"),
    ("m3_rating_distribution.csv",   "~15 rows", "SQL Query 5"),
    ("m3_at_risk_rate.csv",          "3 rows",   "SQL Query 6"),
    ("m3_category_refund_rates.csv", "6 rows",   "SQL Query 7"),
    ("m3_experience_combo.csv",      "4 rows",   "SQL Query 8"),
]
PY_FILES = [
    ("m3_category_platform.csv",     "~18 rows", "Python Cell 2"),
    ("m3_value_retention.csv",       "~12 rows", "Python Cell 3"),
]

print("\n=== OUTPUT FILE CHECKLIST ===")
print("\nSQL exports (save from pgAdmin):")
for fname, rows, source in SQL_FILES:
    exists = "✓" if os.path.exists(f"{OUTDIR}/{fname}") else "✗ missing"
    print(f"  {exists}  {fname:<40} {rows:<10} {source}")

print("\nPython exports (this script):")
for fname, rows, source in PY_FILES:
    exists = "✓" if os.path.exists(f"{OUTDIR}/{fname}") else "✗ missing"
    print(f"  {exists}  {fname:<40} {rows:<10} {source}")

print("\nAll 10 files → connect to Tableau Public")
print("Workbook name  : Quick-Commerce-Wars-M3")
print("Dashboard name : M3 Customer Retention Analysis")
