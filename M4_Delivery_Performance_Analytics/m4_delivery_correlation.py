# ================================================================
# Quick Commerce Wars
# Module 4: Delivery Performance Analytics — Python Script
# ================================================================
# ================================================================

import pandas as pd
import numpy as np
from scipy import stats
import os
import warnings
warnings.filterwarnings('ignore')

# ── Paths ────────────────────────────────────────────────────
CLEAN  = "/content/drive/MyDrive/QuickCommerceWars/data/cleaned"
OUTDIR = "/content/drive/MyDrive/QuickCommerceWars/data/m4_outputs"
os.makedirs(OUTDIR, exist_ok=True)


# ================================================================
# CELL 1: Load and verify data
# ================================================================

df = pd.read_csv(f"{CLEAN}/qc_main_cleaned.csv")

print("=== DATA LOADED ===")
print(f"Shape: {df.shape}")
print(f"\nDelivery time range : {df['delivery_time_min'].min():.1f} – {df['delivery_time_min'].max():.1f} min")
print(f"Distance range      : {df['distance_km'].min():.1f} – {df['distance_km'].max():.1f} km")
print(f"\nCompany counts:")
print(df['company'].value_counts().to_string())


# ================================================================
# CELL 2: Pearson Correlation — Distance vs Delivery Time
# ================================================================
# Purpose : Quantify how much of delivery time is explained by
#           distance alone. Pearson r measures linear correlation.
#           R² (r²) gives the % of variance explained.
#
# Why this matters:
#   If R² ≈ 0.25, distance explains only 25% of delivery time.
#   That means 75% is driven by other factors — store prep time,
#   traffic, partner skill, time of day. This is the root cause
#   finding: improving prep time has more impact than shorter routes.
#
# Interpretation guide:
#   r > 0.7 = strong linear relationship
#   r = 0.4–0.7 = moderate
#   r < 0.4 = weak — distance is not the main driver

print("\n=== PEARSON CORRELATION: DISTANCE vs DELIVERY TIME ===")
print(f"{'Company':<22} {'r (Pearson)':<16} {'R² (variance explained)'}")
print("-" * 60)

corr_results = []

for company in sorted(df['company'].unique()):
    sub = df[df['company'] == company].dropna(
        subset=['distance_km', 'delivery_time_min']
    )

    r, p_value = stats.pearsonr(sub['distance_km'], sub['delivery_time_min'])
    r_squared  = r ** 2

    corr_results.append({
        'company'           : company,
        'pearson_r'         : round(r, 4),
        'r_squared'         : round(r_squared, 4),
        'variance_explained': f"{r_squared * 100:.1f}%",
        'p_value'           : round(p_value, 6),
        'n_orders'          : len(sub),
    })

    print(f"  {company:<20} {r:<16.4f} {r_squared * 100:.1f}%  (p={p_value:.2e})")

corr_df = pd.DataFrame(corr_results)

print(f"\nInterpretation:")
for _, row in corr_df.iterrows():
    if row['r_squared'] < 0.30:
        interpretation = "Weak — prep time and city traffic are bigger delay drivers than distance"
    elif row['r_squared'] < 0.60:
        interpretation = "Moderate — distance matters but is not the dominant factor"
    else:
        interpretation = "Strong — delivery time is largely distance-driven"
    print(f"  {row['company']}: {interpretation}")

corr_df.to_csv(f"{OUTDIR}/m4_correlations.csv", index=False)
print(f"\nSaved → {OUTDIR}/m4_correlations.csv")
print("Tableau: Use as a text annotation on the delivery scatter plot")


# ================================================================
# CELL 3: Statistical Outlier Cities
# ================================================================
# Purpose : Flag cities where slow_order_pct is statistically
#           unusual (more than 2 standard deviations above the
#           mean for that company).
#
# Why z-score vs SQL threshold (>30 min):
#   SQL Query 6 flags cities where slow orders > 30 min.
#   That threshold is fixed. Z-score is relative — it flags
#   cities that are abnormally slow compared to that company's
#   OWN average. A city that is 2σ above average is a genuine
#   operational outlier regardless of the absolute time.

print("\n=== STATISTICAL OUTLIER CITY DETECTION ===")
print("Flagging cities where slow_order_pct > 2 standard deviations above company mean\n")

city_agg = (
    df[df['city'] != 'Unknown']
    .groupby(['company', 'city'])
    .agg(
        total_orders     = ('order_id',          'count'),
        avg_delivery_min = ('delivery_time_min', 'mean'),
        p90_delivery_min = ('delivery_time_min', lambda x: np.percentile(x, 90)),
        slow_orders      = ('delivery_time_min', lambda x: (x > 30).sum()),
        avg_distance_km  = ('distance_km',       'mean'),
        avg_efficiency   = ('delivery_time_min', lambda x: (
            df.loc[x.index, 'distance_km'] / x.replace(0, np.nan)
        ).mean()),
    )
    .reset_index()
)

city_agg['slow_order_pct'] = (
    city_agg['slow_orders'] / city_agg['total_orders'] * 100
).round(2)

city_agg['avg_delivery_min'] = city_agg['avg_delivery_min'].round(2)
city_agg['p90_delivery_min'] = city_agg['p90_delivery_min'].round(2)
city_agg['avg_efficiency']   = city_agg['avg_efficiency'].round(4)

# Z-score within each company
city_agg['zscore_slow_pct'] = (
    city_agg.groupby('company')['slow_order_pct']
    .transform(lambda x: stats.zscore(x, ddof=1))
).round(3)

# Flag outliers
city_agg['is_outlier'] = (city_agg['zscore_slow_pct'] > 2.0).astype(int)

# Filter to cities with >= 100 orders (exclude noise)
city_agg = city_agg[city_agg['total_orders'] >= 100].copy()

outliers = city_agg[city_agg['is_outlier'] == 1].sort_values('zscore_slow_pct', ascending=False)

if len(outliers) > 0:
    print(f"Outlier cities found ({len(outliers)}):")
    print(outliers[[
        'company', 'city', 'total_orders',
        'slow_order_pct', 'zscore_slow_pct', 'avg_delivery_min'
    ]].to_string(index=False))
else:
    print("No outlier cities found at z > 2.0 threshold.")
    print("(This can happen if the distribution is fairly uniform.)")

city_agg.to_csv(f"{OUTDIR}/m4_city_outliers_flagged.csv", index=False)
print(f"\nFull city table saved → {OUTDIR}/m4_city_outliers_flagged.csv")
print("Tableau: Join to m4_city_performance.csv on city+company")
print("         Colour outlier cities red in the heatmap using is_outlier field")


# ================================================================
# CELL 4: Output checklist
# ================================================================

SQL_FILES = [
    ("m4_company_performance.csv",    "3 rows",   "SQL Query 1"),
    ("m4_city_performance.csv",       "~36 rows", "SQL Query 2"),
    ("m4_speed_distribution.csv",     "~12 rows", "SQL Query 3"),
    ("m4_partner_tiers.csv",          "~12 rows", "SQL Query 4"),
    ("m4_distance_buckets.csv",       "~12 rows", "SQL Query 5"),
    ("m4_outlier_cities.csv",         "~20 rows", "SQL Query 6"),
    ("m4_city_rankings.csv",          "~36 rows", "SQL Query 7"),
]
PY_FILES = [
    ("m4_correlations.csv",           "3 rows",   "Python Cell 2"),
    ("m4_city_outliers_flagged.csv",  "~36 rows", "Python Cell 3"),
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

print("\nAll 9 files → connect to Tableau Public")
print("Workbook name  : Quick-Commerce-Wars-M4")
print("Dashboard name : M4 Delivery Performance Analytics")
