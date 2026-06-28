# ================================================================
# Quick Commerce Wars
# Module 2: Dark Store Expansion Analysis — Python Script
# ================================================================
#
# Purpose : Join dark store data with India census demographics,
#           calculate an opportunity score per city per company,
#           then produce a composite expansion priority score
#           that combines 4 signals into a single ranked table.
#
# Why Python owns this (not SQL):
#   The census table and dark_stores table live in the same
#   PostgreSQL database, but the join requires city-name
#   normalisation between the two datasets (e.g. "Bengaluru"
#   in stores vs "BANGALORE" in census). This string-matching
#   logic is cleaner in Python. All GROUP BY aggregations
#   stay in SQL (m2_dark_store_expansion.sql).
#
# Inputs  :
#   data/cleaned/dark_stores_combined.csv
#   data/cleaned/india_census_urban.csv
#
# Outputs (saved to data/m2_outputs/):
#   m2_composite_priority.csv    → Tableau 2×2 priority matrix
#   m2_expansion_blinkit.csv     → Top 10 cities for Blinkit
#   m2_expansion_swiggy_instamart.csv
#   m2_expansion_zepto.csv
#   m2_metro_density.csv         → Tableau metro comparison chart
# ================================================================

import pandas as pd
import numpy as np
import os
import warnings
warnings.filterwarnings('ignore')

# ── Paths ────────────────────────────────────────────────────
CLEAN  = "/content/drive/MyDrive/QuickCommerceWars/data/cleaned"
OUTDIR = "/content/drive/MyDrive/QuickCommerceWars/data/m2_outputs"
os.makedirs(OUTDIR, exist_ok=True)


# ================================================================
# CELL 1: Load data
# ================================================================

stores = pd.read_csv(f"{CLEAN}/dark_stores_combined.csv")
census = pd.read_csv(f"{CLEAN}/india_census_urban.csv")

print("=== DATA LOADED ===")
print(f"dark_stores_combined : {stores.shape}  | Companies: {stores['company'].value_counts().to_dict()}")
print(f"india_census_urban   : {census.shape}  | Columns: {list(census.columns)}")

# Quick coverage check
print(f"\nUnique cities in stores : {stores['city'].nunique()}")
print(f"Top 10 cities by stores :")
print(stores['city'].value_counts().head(10).to_string())


# ================================================================
# CELL 2: Pivot store counts to wide format (one row per city)
# ================================================================

density_pivot = (
    stores[stores['city'] != 'Unknown']
    .groupby(['city', 'company'])
    .size()
    .unstack(fill_value=0)
    .reset_index()
)

# Ensure all three companies have a column even if absent in some cities
for co in ['Blinkit', 'Swiggy Instamart', 'Zepto']:
    if co not in density_pivot.columns:
        density_pivot[co] = 0

density_pivot['total_stores'] = (
    density_pivot['Blinkit'] +
    density_pivot['Swiggy Instamart'] +
    density_pivot['Zepto']
)

print(f"\n=== STORE DENSITY PIVOT ===")
print(f"Shape: {density_pivot.shape}  (one row per city)")
print(density_pivot.sort_values('total_stores', ascending=False).head(10).to_string(index=False))


# ================================================================
# CELL 3: City-to-district name mapping for census join
# ================================================================
CITY_TO_DISTRICT = {
    'BENGALURU'    : 'BANGALORE',
    'DELHI/NCR'    : 'NEW DELHI',
    'AHMEDABAD'    : 'AHMADABAD',
    'MYSURU'       : 'MYSORE',
    'PRAYAGRAJ'    : 'ALLAHABAD',
    'SAS NAGAR'    : 'S.A.S. NAGAR',
    'GURUGRAM'     : 'GURGAON',
    'NOIDA'        : 'GAUTAM BUDDHA NAGAR',
    'VIJAYAWADA'   : 'KRISHNA',
    'NAVI MUMBAI'  : 'THANE',
    'SILIGURI'     : 'JALPAIGURI',
}

def map_to_district(city_name):
    upper = str(city_name).upper().strip()
    return CITY_TO_DISTRICT.get(upper, upper)

density_pivot['district_key'] = density_pivot['city'].apply(map_to_district)
census['district_key']        = census['district_name'].str.upper().str.strip()

print(f"\n=== CITY → DISTRICT MAPPING ===")
print(f"Mapped {len(CITY_TO_DISTRICT)} city names to census district names")
print(f"Unmapped cities default to their own name (uppercase)")


# ================================================================
# CELL 4: Join stores with census demographics
# ================================================================

merged = density_pivot.merge(
    census[['district_key', 'urban_population', 'households',
            'literacy_rate', 'avg_household_size']],
    on='district_key',
    how='left'
)

matched   = merged['urban_population'].notna().sum()
unmatched = merged['urban_population'].isna().sum()
print(f"\n=== CENSUS JOIN RESULT ===")
print(f"Cities matched to census : {matched}")
print(f"Cities unmatched (Tier 3): {unmatched}  (filled with 0 for scoring)")

# IMPORTANT: fillna BEFORE any arithmetic — prevents NaN propagating
# into scores and silently producing all-zero results
merged['urban_population']   = merged['urban_population'].fillna(0).astype(int)
merged['households']         = merged['households'].fillna(0).astype(int)
merged['literacy_rate']      = merged['literacy_rate'].fillna(0)
merged['avg_household_size'] = merged['avg_household_size'].fillna(0)

print(merged[['city', 'Blinkit', 'Swiggy Instamart', 'Zepto',
              'total_stores', 'households', 'literacy_rate']].head(10).to_string(index=False))


# ================================================================
# CELL 5: Opportunity Score
# ================================================================
# Formula:
#   opportunity_score = (households × literacy_rate / 100)
#                       ÷ (company_stores + 1)
#
# Why households (not urban_population)?
#   Quick commerce is driven by household orders, not individuals.
#   A household of 4 generates ~1 order, not 4 orders.
#   Households is a better proxy for addressable demand.
#
# Why company_stores (not total_stores)?
#   Each company's opportunity is independent of its rivals.
#   Blinkit having 0 stores in a city is a Blinkit-specific
#   opportunity, regardless of how many Zepto stores are there.
#
# Why +1?
#   Prevents division by zero for cities with 0 current stores.
#   Also models the marginal opportunity of the NEXT store.

print("\n=== OPPORTUNITY SCORE CALCULATION ===")

for company in ['Blinkit', 'Swiggy Instamart', 'Zepto']:
    col = company.lower().replace(' ', '_') + '_opp_score'
    merged[col] = (
        (merged['households'] * merged['literacy_rate'] / 100)
        / (merged[company] + 1)
    ).round(0).fillna(0).astype(int)
    print(f"  {company:<20}: score range {merged[col].min():,} – {merged[col].max():,}")

print(f"\nTop 5 cities by Blinkit opportunity:")
print(merged.nlargest(5, 'blinkit_opp_score')
      [['city', 'Blinkit', 'households', 'literacy_rate', 'blinkit_opp_score']]
      .to_string(index=False))


# ================================================================
# CELL 6: White-Space Analysis
# ================================================================
# A city is "white-space" for a company if it has 0 stores there.
# This is the highest-urgency expansion signal — the company
# has no presence at all, meaning 100% of potential customers
# are using a competitor.

print("\n=== WHITE-SPACE ANALYSIS ===")

for company in ['Blinkit', 'Swiggy Instamart', 'Zepto']:
    absent = (merged[company] == 0).sum()
    present = (merged[company] > 0).sum()
    print(f"  {company:<20}: present in {present} cities | absent in {absent} cities")

# Flag each city per company
merged['blinkit_absent']       = (merged['Blinkit'] == 0).astype(int)
merged['swiggy_absent']        = (merged['Swiggy Instamart'] == 0).astype(int)
merged['zepto_absent']         = (merged['Zepto'] == 0).astype(int)

# Cities where ALL THREE companies are absent = untapped markets
merged['all_absent'] = (
    (merged['Blinkit'] == 0) &
    (merged['Swiggy Instamart'] == 0) &
    (merged['Zepto'] == 0)
).astype(int)

print(f"\n  Cities with no company at all: {merged['all_absent'].sum()}")


# ================================================================
# CELL 7: Metro Density (stores per million households)
# ================================================================
# Raw store count is misleading — Mumbai with 200 stores serving
# 4M households is actually thinner coverage than Pune with 50
# stores serving 500K households.
# Normalising by households gives a fair coverage comparison.

print("\n=== METRO DENSITY (stores per million households) ===")

metro = merged[merged['households'] > 200000].copy()

for company in ['Blinkit', 'Swiggy Instamart', 'Zepto']:
    col = company.lower().replace(' ', '_') + '_per_million_hh'
    metro[col] = (
        metro[company] / (metro['households'] / 1_000_000)
    ).replace([np.inf], 0).fillna(0).round(1)

metro_display = metro[[
    'city', 'households',
    'Blinkit', 'Swiggy Instamart', 'Zepto',
    'blinkit_per_million_hh', 'swiggy_instamart_per_million_hh', 'zepto_per_million_hh'
]].sort_values('blinkit_per_million_hh', ascending=False)

print(metro_display.head(12).to_string(index=False))
metro_display.to_csv(f"{OUTDIR}/m2_metro_density.csv", index=False)
print("Saved ✓  →  m2_metro_density.csv")


# ================================================================
# CELL 8: Composite Expansion Priority Score
# ================================================================
# A single opportunity score is not enough to rank cities for
# expansion. A city can be a great market but already well-served.
#
# This score combines 4 signals:
#
#   Signal 1 — Opportunity      (40%) — market size × literacy ÷ stores
#   Signal 2 — Coverage gap     (30%) — how thin is our presence?
#   Signal 3 — White-space      (20%) — are we completely absent?
#   Signal 4 — Competitive gap  (10%) — how far behind the leader?
#
# Each signal is min-max normalised to 0–1 before weighting.
# This ensures no single signal dominates due to its raw scale.
#
# The weights are strategic assumptions you can defend in an
# interview: opportunity matters most, followed by coverage
# gaps, then urgency of being absent, then competitor pressure.

def min_max(series):
    """Normalise a series to 0–1 range."""
    rng = series.max() - series.min()
    if rng == 0:
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (series - series.min()) / rng

all_priorities = []

for company in ['Blinkit', 'Swiggy Instamart', 'Zepto']:
    col       = company.lower().replace(' ', '_')
    opp_col   = f"{col}_opp_score"
    absent_col= f"{col}_absent"

    # Filter to cities with meaningful population
    df = merged[merged['households'] > 50000].copy()

    # Signal 1: Opportunity score
    df['sig_opportunity'] = min_max(df[opp_col])

    # Signal 2: Coverage gap (stores per million HH — inverted)
    df['stores_per_million_hh'] = (
        df[company] / (df['households'] / 1_000_000)
    ).replace([np.inf], 0).fillna(0)
    df['sig_coverage'] = 1 - min_max(df['stores_per_million_hh'])

    # Signal 3: White-space (binary — 0 stores = 1, else = 0)
    df['sig_whitespace'] = df[absent_col].astype(float)

    # Signal 4: Competitive gap vs market leader
    df['leader_stores']    = df[['Blinkit', 'Swiggy Instamart', 'Zepto']].max(axis=1)
    df['competitive_gap']  = (df['leader_stores'] - df[company]).clip(lower=0)
    df['sig_competitive']  = min_max(df['competitive_gap'])

    # Weighted composite score
    df['expansion_priority'] = (
        df['sig_opportunity']  * 0.40 +
        df['sig_coverage']     * 0.30 +
        df['sig_whitespace']   * 0.20 +
        df['sig_competitive']  * 0.10
    ).round(4)

    df['company'] = company

    # Top 10 for this company
    top10 = df.nlargest(10, 'expansion_priority').copy()
    top10['rank'] = range(1, 11)

    print(f"\n=== TOP 10 EXPANSION CITIES — {company.upper()} ===")
    print(top10[[
        'rank', 'city', 'households', company,
        'expansion_priority', 'sig_opportunity',
        'sig_coverage', 'sig_whitespace', 'sig_competitive'
    ]].to_string(index=False))

    # Save per-company file
    safe_name = col
    top10.to_csv(f"{OUTDIR}/m2_expansion_{safe_name}.csv", index=False)
    print(f"Saved ✓  →  m2_expansion_{safe_name}.csv")

    all_priorities.append(df)

# ================================================================
# CELL 9: Save combined priority file for Tableau 2×2 matrix
# ================================================================
# Tableau chart: X = sig_opportunity, Y = sig_coverage,
# Dot size = households, Colour = sig_whitespace,

combined_priority = pd.concat(all_priorities, ignore_index=True)
combined_priority.to_csv(f"{OUTDIR}/m2_composite_priority.csv", index=False)
print(f"\n=== ALL FILES SAVED ===")

OUTPUT_FILES = [
    ("m2_metro_density.csv",              "from Cell 7 — metro comparison chart"),
    ("m2_composite_priority.csv",         "from Cell 9 — 2×2 Tableau priority matrix"),
    ("m2_expansion_blinkit.csv",          "from Cell 8 — top 10 cities for Blinkit"),
    ("m2_expansion_swiggy_instamart.csv", "from Cell 8 — top 10 for Swiggy Instamart"),
    ("m2_expansion_zepto.csv",            "from Cell 8 — top 10 cities for Zepto"),
]
print(f"\n{'File':<45} {'Source'}")
print("-" * 75)
for fname, source in OUTPUT_FILES:
    exists = "✓" if os.path.exists(f"{OUTDIR}/{fname}") else "✗ missing"
    print(f"  {exists}  {fname:<43} {source}")

print("\nConnect all files to Tableau Public")
print("Workbook name  : Quick-Commerce-Wars-M2")
print("Dashboard name : M2 Dark Store Expansion")
