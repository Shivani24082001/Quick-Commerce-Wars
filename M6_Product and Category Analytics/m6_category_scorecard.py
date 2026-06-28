# ================================================================
# Quick Commerce Wars
# Module 6: Product & Category Analytics — Python Script
# ================================================================
# ================================================================

import pandas as pd
import numpy as np
import os
import warnings
warnings.filterwarnings('ignore')

# ── Paths ────────────────────────────────────────────────────
CLEAN  = "/content/drive/MyDrive/QuickCommerceWars/data/cleaned"
OUTDIR = "/content/drive/MyDrive/QuickCommerceWars/data/m6_outputs"
os.makedirs(OUTDIR, exist_ok=True)


# ================================================================
# CELL 1: Load both datasets
# ================================================================

qc = pd.read_csv(f"{CLEAN}/qc_main_cleaned.csv")
ea = pd.read_csv(f"{CLEAN}/ecommerce_analytics_cleaned.csv")

print("=== DATA LOADED ===")
print(f"qc_main             : {qc.shape}")
print(f"ecommerce_analytics : {ea.shape}")

# Verify category names align — join will silently fail if they don't
qc_cats = set(qc['product_category'].dropna().unique())
ea_cats  = set(ea['product_category'].dropna().unique())
common   = qc_cats & ea_cats
only_qc  = qc_cats - ea_cats
only_ea  = ea_cats - qc_cats

print(f"\nCategories in both datasets : {sorted(common)}")
if only_qc:
    print(f"⚠ In qc_main only           : {sorted(only_qc)}")
if only_ea:
    print(f"⚠ In ecommerce only         : {sorted(only_ea)}")

if len(common) == 0:
    raise ValueError("No matching category names — check cleaning step")


# ================================================================
# CELL 2: Aggregate each dataset to category level
# ================================================================

# Side A — Revenue & satisfaction metrics from qc_main
qc_agg = qc.groupby('product_category').agg(
    total_orders    = ('order_id',             'count'),
    revenue_millions= ('order_value',          lambda x: round(x.sum() / 1_000_000, 3)),
    avg_order_value = ('order_value',          lambda x: round(x.mean(), 2)),
    avg_rating      = ('customer_rating',      lambda x: round(x.mean(), 3)),
    discount_rate   = ('is_discounted',        lambda x: round(x.mean() * 100, 2)),
    avg_items       = ('items_count',          lambda x: round(x.mean(), 2)),
).reset_index()

# Discount lift: (avg AOV with discount - avg AOV without) / avg AOV without
disc_aov = qc[qc['is_discounted'] == 1].groupby('product_category')['order_value'].mean()
full_aov = qc[qc['is_discounted'] == 0].groupby('product_category')['order_value'].mean()
lift     = ((disc_aov - full_aov) / full_aov * 100).round(2).rename('discount_lift_pct')
qc_agg   = qc_agg.merge(lift.reset_index(), on='product_category', how='left')

print("\n=== QC_MAIN SIDE (revenue + ratings) ===")
print(qc_agg.sort_values('revenue_millions', ascending=False).to_string(index=False))

# Side B — Refund & satisfaction metrics from ecommerce_analytics
ea_agg = ea.groupby('product_category').agg(
    refund_rate_pct  = ('refund_rate',     lambda x: round(x.mean() * 100, 2)),
    satisfaction_pct = ('is_satisfied',    lambda x: round(x.mean() * 100, 2)),
    at_risk_pct      = ('is_at_risk',      lambda x: round(x.mean() * 100, 2)),
    avg_frequency    = ('order_frequency', lambda x: round(x.mean(), 2)),
).reset_index()

print("\n=== ECOMMERCE_ANALYTICS SIDE (refund + satisfaction) ===")
print(ea_agg.to_string(index=False))


# ================================================================
# CELL 3: Join and build composite risk score
# ================================================================
# Join on product_category (same 6 names in both datasets)

scorecard = qc_agg.merge(ea_agg, on='product_category', how='left')

# Fill any unmatched categories
fill_cols = ['refund_rate_pct', 'satisfaction_pct', 'at_risk_pct', 'avg_frequency']
scorecard[fill_cols] = scorecard[fill_cols].fillna(0)

# ── Composite risk score ──────────────────────────────────────
# Risk score = weighted combination of 3 bad-experience signals:
#   50% — refund rate (most direct quality failure signal)
#   30% — inverse of avg_rating (rating from qc_main, not ea)
#   20% — at-risk customer % (from ecommerce_analytics)
#
# Higher risk_score = category has poor customer experience.
# Revenue vs risk_score plotted as a bubble chart in Tableau:
#   X axis = revenue_millions
#   Y axis = risk_score
#   Bubble size = total_orders
#   Top-right quadrant = high revenue + high risk = most urgent
#
# Why this weighting?
#   Refunds are the most direct signal of product quality failure.
#   Ratings capture overall experience but are noisier.
#   At-risk % shows long-term retention impact.

scorecard['risk_score'] = (
    scorecard['refund_rate_pct']                     * 0.50 +
    (5 - scorecard['avg_rating'])                    * 10 * 0.30 +
    scorecard['at_risk_pct']                         * 0.20
).round(3)

# Revenue vs risk quadrant label (for Tableau filter)
rev_median  = scorecard['revenue_millions'].median()
risk_median = scorecard['risk_score'].median()

def quadrant_label(row):
    high_rev  = row['revenue_millions'] >= rev_median
    high_risk = row['risk_score']       >= risk_median
    if high_rev and high_risk:
        return '1. High Revenue / High Risk — Invest Now'
    elif high_rev and not high_risk:
        return '2. High Revenue / Low Risk — Protect'
    elif not high_rev and high_risk:
        return '3. Low Revenue / High Risk — Monitor'
    else:
        return '4. Low Revenue / Low Risk — Maintain'

scorecard['quadrant'] = scorecard.apply(quadrant_label, axis=1)

print("\n=== CROSS-DATASET SCORECARD ===")
display_cols = [
    'product_category', 'revenue_millions', 'avg_order_value',
    'avg_rating', 'discount_rate', 'discount_lift_pct',
    'refund_rate_pct', 'satisfaction_pct', 'risk_score', 'quadrant'
]
print(scorecard[display_cols].sort_values('revenue_millions', ascending=False)
      .to_string(index=False))

print("\n=== PRIORITY QUADRANT SUMMARY ===")
print(scorecard[['product_category', 'quadrant']]
      .sort_values('quadrant').to_string(index=False))

outpath = f"{OUTDIR}/m6_cross_dataset_scorecard.csv"
scorecard.to_csv(outpath, index=False)
print(f"\nSaved ({len(scorecard)} rows) → {outpath}")


# ================================================================
# CELL 4: Output checklist
# ================================================================

SQL_FILES = [
    ("m6_category_revenue.csv",      "6 rows",   "SQL Query 1"),
    ("m6_category_company.csv",      "~18 rows", "SQL Query 2"),
    ("m6_discount_dependency.csv",   "6 rows",   "SQL Query 3"),
    ("m6_category_ratings.csv",      "~18 rows", "SQL Query 4"),
    ("m6_basket_analysis.csv",       "~72 rows", "SQL Query 5"),
    ("m6_scorecard.csv",             "6 rows",   "SQL Query 6"),
]
PY_FILES = [
    ("m6_cross_dataset_scorecard.csv", "6 rows", "Python Cell 3 — Revenue vs Risk bubble chart"),
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

print("\nAll 7 files → connect to Tableau Public")
print("Workbook name  : Quick-Commerce-Wars-M6")
print("Dashboard name : M6 Product & Category Analytics")
print("\nKey chart: Revenue vs Risk bubble (m6_cross_dataset_scorecard.csv)")
print("  X = revenue_millions  |  Y = risk_score")
print("  Size = total_orders   |  Colour = quadrant")
