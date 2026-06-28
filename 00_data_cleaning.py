# ================================================================
# Quick Commerce Wars
# 00_data_cleaning.py — Master Data Cleaning Pipeline
# ================================================================
# Author  : [Your Name]
# Tool    : Google Colab (Python 3.10+)
# Run     : ONCE, before any module. All other scripts depend
#           on the cleaned CSVs this produces.
#
# Inputs  (place in Google Drive → QuickCommerceWars/data/raw/):
#   quick_commerce_raw.csv
#   ecommerce_delivery_analytics.csv
#   blinkit-darkstores.csv
#   swiggy-darkstores.csv
#   zepto-darkstores.csv
#   2011-IndiaStateDist-0000.xlsx
#
# Outputs (saved to QuickCommerceWars/data/cleaned/):
#   qc_main_cleaned.csv
#   ecommerce_analytics_cleaned.csv
#   dark_stores_combined.csv
#   india_census_urban.csv
#   cleaning_report.txt
#
# Runtime: ~5–10 minutes (reverse geocoding is the slow step)
# ================================================================

import pandas as pd
import numpy as np
import os
import warnings
from datetime import datetime
warnings.filterwarnings('ignore')

# ── Install reverse geocoder (Colab only) ────────────────────
# Uncomment and run once on first use:
# !pip install reverse_geocoder --quiet
import reverse_geocoder as rg

# ── Paths — update to your Google Drive folder ───────────────
RAW   = "/content/drive/MyDrive/QuickCommerceWars/data/raw"
CLEAN = "/content/drive/MyDrive/QuickCommerceWars/data/cleaned"
os.makedirs(CLEAN, exist_ok=True)

# ── Logging helper ────────────────────────────────────────────
log_lines = []
def log(msg):
    print(msg)
    log_lines.append(msg)

def section(title):
    line = "=" * 65
    log(f"\n{line}\n  {title}\n{line}")


# ================================================================
# SECTION 1: qc_main — Main Orders Table (~375K rows)
# ================================================================
section("1. QC_MAIN — MAIN ORDERS TABLE")

df = pd.read_csv(f"{RAW}/quick_commerce_raw.csv")
log(f"Raw shape: {df.shape}")
log(f"Columns  : {list(df.columns)}")

# ── 1.1 Rename columns to snake_case ─────────────────────────
df.rename(columns={
    'Order ID'               : 'order_id',
    'Company'                : 'company',
    'City'                   : 'city',
    'Customer Age'           : 'customer_age',
    'Order Value (INR)'      : 'order_value',
    'Delivery Time (Minutes)': 'delivery_time_min',
    'Distance (km)'          : 'distance_km',
    'Number of Items'        : 'items_count',
    'Product Category'       : 'product_category',
    'Payment Method'         : 'payment_method',
    'Customer Rating'        : 'customer_rating',
    'Discount Applied'       : 'is_discounted',
    'Delivery Partner Rating': 'delivery_partner_rating',
}, inplace=True)

# ── 1.2 Standardise company names ────────────────────────────
# Raw data may have inconsistent casing or extra spaces
COMPANY_MAP = {
    'blinkit'          : 'Blinkit',
    'BLINKIT'          : 'Blinkit',
    'zepto'            : 'Zepto',
    'ZEPTO'            : 'Zepto',
    'swiggy instamart' : 'Swiggy Instamart',
    'SWIGGY INSTAMART' : 'Swiggy Instamart',
    'Swiggy'           : 'Swiggy Instamart',
    'swiggy'           : 'Swiggy Instamart',
}
df['company'] = df['company'].str.strip().replace(COMPANY_MAP)
log(f"\nCompany counts after standardisation:")
log(df['company'].value_counts().to_string())

# ── 1.3 Standardise city names ────────────────────────────────
df['city'] = df['city'].str.strip().str.title().fillna('Unknown')

# ── 1.4 Drop duplicates ───────────────────────────────────────
before = len(df)
df.drop_duplicates(subset='order_id', keep='first', inplace=True)
log(f"\nDuplicates removed: {before - len(df)}")

# ── 1.5 Handle nulls ─────────────────────────────────────────
# Numeric columns: fill with median (not mean — avoids outlier skew)
for col in ['order_value', 'delivery_time_min', 'distance_km',
            'customer_age', 'items_count']:
    null_count = df[col].isnull().sum()
    if null_count > 0:
        df[col] = df[col].fillna(df[col].median())
        log(f"  Filled {null_count} nulls in {col} with median")

# Rating columns: fill with column median
for col in ['customer_rating', 'delivery_partner_rating']:
    null_count = df[col].isnull().sum()
    if null_count > 0:
        df[col] = df[col].fillna(df[col].median())
        log(f"  Filled {null_count} nulls in {col} with median")

# is_discounted: binary — fill nulls with 0 (assume no discount)
df['is_discounted'] = df['is_discounted'].fillna(0).astype(int)

# ── 1.6 Fix data types ────────────────────────────────────────
# IMPORTANT: fillna() MUST happen before astype(int)
# or you get IntCastingNaNError on any remaining NaN values
df['order_id']     = df['order_id'].astype(int)
df['customer_age'] = df['customer_age'].fillna(0).astype(int)
df['items_count']  = df['items_count'].fillna(0).astype(int)
df['order_value']  = df['order_value'].round(2)
df['delivery_time_min'] = df['delivery_time_min'].round(2)
df['distance_km']  = df['distance_km'].round(2)

# ── 1.7 Add derived columns ───────────────────────────────────
# These are used directly in SQL queries across M1–M7.
# Adding them here avoids ALTER TABLE + UPDATE in PostgreSQL.

q75 = df['order_value'].quantile(0.75)

df['order_value_bucket'] = pd.cut(
    df['order_value'],
    bins=[0, 200, 500, 1000, float('inf')],
    labels=['Budget (<₹200)', 'Mid (₹200-500)',
            'Premium (₹500-1k)', 'High-Value (>₹1k)'],
    right=True
).astype(str)

df['delivery_speed_bucket'] = pd.cut(
    df['delivery_time_min'],
    bins=[0, 10, 20, 30, float('inf')],
    labels=['Express (<10 min)', 'Fast (10-20 min)',
            'Standard (20-30 min)', 'Slow (>30 min)'],
    right=True
).astype(str)

df['distance_bucket'] = pd.cut(
    df['distance_km'],
    bins=[0, 3, 7, 12, float('inf')],
    labels=['Nearby (<3 km)', 'Short (3-7 km)',
            'Medium (7-12 km)', 'Long (>12 km)'],
    right=True
).astype(str)

df['revenue_per_km'] = (
    df['order_value'] / df['distance_km'].replace(0, np.nan)
).round(2).fillna(0)

df['is_high_value'] = (df['order_value'] > q75).astype(int)

log(f"\nDerived columns added:")
log(f"  order_value_bucket      : {df['order_value_bucket'].value_counts().to_dict()}")
log(f"  delivery_speed_bucket   : {df['delivery_speed_bucket'].value_counts().to_dict()}")
log(f"  distance_bucket         : {df['distance_bucket'].value_counts().to_dict()}")
log(f"  is_high_value (75th pct): threshold = ₹{q75:.0f}, flagged = {df['is_high_value'].sum():,}")

# ── 1.8 Final validation ─────────────────────────────────────
log(f"\nFinal shape   : {df.shape}")
log(f"Remaining nulls: {df.isnull().sum().sum()}")
log(f"\nSample row:")
log(df.iloc[0].to_string())

df.to_csv(f"{CLEAN}/qc_main_cleaned.csv", index=False)
log(f"\nSaved → {CLEAN}/qc_main_cleaned.csv")


# ================================================================
# SECTION 2: ecommerce_analytics — Customer Delivery Analytics
# ================================================================
section("2. ECOMMERCE_ANALYTICS")

ea = pd.read_csv(f"{RAW}/ecommerce_delivery_analytics.csv")
log(f"Raw shape: {ea.shape}")
log(f"Columns  : {list(ea.columns)}")

# ── 2.1 Rename columns ───────────────────────────────────────
ea.rename(columns={
    'Order ID'               : 'order_id',
    'Platform'               : 'company',
    'Delivery Time (Minutes)': 'delivery_time_min',
    'Product Category'       : 'product_category',
    'Order Value (INR)'      : 'order_value',
    'Customer Feedback'      : 'customer_feedback',
    'Service Rating'         : 'service_rating',
    'Delivery Delay'         : 'had_delay',
    'Refund Requested'       : 'had_refund',
}, inplace=True)

# ── 2.2 Standardise company names ────────────────────────────
ea['company'] = ea['company'].str.strip().replace(COMPANY_MAP)

# ── 2.3 Drop duplicates ───────────────────────────────────────
before = len(ea)
ea.drop_duplicates(subset='order_id', keep='first', inplace=True)
log(f"Duplicates removed: {before - len(ea)}")

# ── 2.4 Handle the corrupted date column ─────────────────────
# The 'Order Date & Time' column in this dataset is corrupted —
# values are not valid timestamps. We drop it entirely.
# Monthly cohort analysis is therefore NOT possible and has been
# replaced with order-frequency segmentation in M3.
DATE_COLS = [c for c in ea.columns if 'date' in c.lower() or 'time' in c.lower()]
if DATE_COLS:
    ea.drop(columns=DATE_COLS, inplace=True, errors='ignore')
    log(f"Dropped corrupted date columns: {DATE_COLS}")

# ── 2.5 Handle nulls ─────────────────────────────────────────
# IMPORTANT: fillna before astype to avoid IntCastingNaNError
ea['had_delay']   = ea['had_delay'].fillna(0).astype(int)
ea['had_refund']  = ea['had_refund'].fillna(0).astype(int)
ea['service_rating'] = ea['service_rating'].fillna(
    ea['service_rating'].median()
).round(2)
ea['order_value'] = ea['order_value'].fillna(
    ea['order_value'].median()
).round(2)
ea['delivery_time_min'] = ea['delivery_time_min'].fillna(
    ea['delivery_time_min'].median()
).round(2)

# ── 2.6 Add derived columns ───────────────────────────────────
# order_frequency: number of orders per customer ID
# Used in M3 (retention segmentation) in place of RFM recency
if 'Customer ID' in ea.columns or 'customer_id' in ea.columns:
    id_col = 'Customer ID' if 'Customer ID' in ea.columns else 'customer_id'
    ea.rename(columns={id_col: 'customer_id'}, inplace=True)
    freq_map = ea['customer_id'].value_counts()
    ea['order_frequency'] = ea['customer_id'].map(freq_map)
else:
    # No customer ID — derive a proxy frequency from value_counts on order_value + company
    log("WARNING: No customer_id column found. order_frequency set to 1.")
    ea['order_frequency'] = 1

# refund_rate per customer (or per row if no customer ID)
ea['refund_rate'] = ea['had_refund'].astype(float)

# Satisfaction flag: service_rating >= 4
ea['is_satisfied'] = (ea['service_rating'] >= 4).astype(int)

# At-risk flag: low frequency AND had a bad experience
ea['is_at_risk'] = (
    (ea['order_frequency'] <= 2) &
    ((ea['had_refund'] == 1) | (ea['had_delay'] == 1))
).astype(int)

# order_value bucket (consistent with qc_main)
ea['order_value_bucket'] = pd.cut(
    ea['order_value'],
    bins=[0, 200, 500, 1000, float('inf')],
    labels=['Budget (<₹200)', 'Mid (₹200-500)',
            'Premium (₹500-1k)', 'High-Value (>₹1k)'],
    right=True
).astype(str)

log(f"\nFinal shape   : {ea.shape}")
log(f"Remaining nulls: {ea.isnull().sum().sum()}")

ea.to_csv(f"{CLEAN}/ecommerce_analytics_cleaned.csv", index=False)
log(f"Saved → {CLEAN}/ecommerce_analytics_cleaned.csv")


# ================================================================
# SECTION 3: Dark Stores — Blinkit, Swiggy, Zepto (3 → 1 file)
# ================================================================
section("3. DARK STORES (3 files → combined)")

# City name standardisation map
# Consolidates sub-localities and spelling variants into clean city names
CITY_MAP = {
    # Delhi NCR
    'Delhi':'Delhi/NCR',       'New Delhi':'Delhi/NCR',
    'Gurugram':'Delhi/NCR',    'Gurgaon':'Delhi/NCR',
    'Noida':'Delhi/NCR',       'Greater Noida':'Delhi/NCR',
    'Ghaziabad':'Delhi/NCR',   'Faridabad':'Delhi/NCR',
    # Mumbai Metro
    'Mumbai':'Mumbai',         'Navi Mumbai':'Mumbai',
    'Thane':'Mumbai',          'Kalyan':'Mumbai',
    'Vasai':'Mumbai',
    # Bengaluru
    'Bengaluru':'Bengaluru',   'Bangalore':'Bengaluru',
    'Whitefield':'Bengaluru',  'Electronic City':'Bengaluru',
    'Koramangala':'Bengaluru', 'Marathahalli':'Bengaluru',
    'Yelahanka':'Bengaluru',   'Bannerghatta':'Bengaluru',
    # Hyderabad
    'Hyderabad':'Hyderabad',   'Secunderabad':'Hyderabad',
    'Cyberabad':'Hyderabad',   'Gachibowli':'Hyderabad',
    'Madhapur':'Hyderabad',
    # Chennai
    'Chennai':'Chennai',       'Adyar':'Chennai',
    'Velachery':'Chennai',     'Porur':'Chennai',
    'Chetput':'Chennai',
    # Ahmedabad
    'Ahmedabad':'Ahmedabad',   'Sarkhej':'Ahmedabad',
    'Adalaj':'Ahmedabad',      'Naroda':'Ahmedabad',
    # Other cities
    'Surat':'Surat',           'Vadodara':'Vadodara',
    'Jaipur':'Jaipur',         'Lucknow':'Lucknow',
    'Kanpur':'Kanpur',         'Indore':'Indore',
    'Nagpur':'Nagpur',         'Chandigarh':'Chandigarh',
    'Ludhiana':'Ludhiana',     'Amritsar':'Amritsar',
    'Bhopal':'Bhopal',         'Patna':'Patna',
    'Agra':'Agra',             'Varanasi':'Varanasi',
    'Pune':'Pune',             'Kolkata':'Kolkata',
    'Kochi':'Kochi',           'Mysore':'Mysuru',
    'Allahabad':'Prayagraj',   'Nashik':'Nashik',
    'Dehradun':'Dehradun',     'Ranchi':'Ranchi',
    'Bhubaneswar':'Bhubaneswar','Bhubaneshwar':'Bhubaneswar',
    'Siliguri':'Siliguri',     'Shiliguri':'Siliguri',
    'Raipur':'Raipur',         'Jamshedpur':'Jamshedpur',
}

def normalise_city(name):
    """Return standardised city name. Falls back to raw name if not in map."""
    if pd.isna(name):
        return 'Unknown'
    return CITY_MAP.get(str(name).strip(), str(name).strip())

FINAL_COLS = ['store_id', 'store_name', 'company', 'city', 'state', 'lat', 'lng']

# ── BLINKIT ──────────────────────────────────────────────────
log("Loading and geocoding Blinkit stores...")
blinkit = pd.read_csv(f"{RAW}/blinkit-darkstores.csv")
blinkit.drop(columns=[c for c in ['accuracy'] if c in blinkit.columns], inplace=True)
blinkit.rename(columns={'id': 'store_id'}, inplace=True)

# Reverse geocode lat/lng → city, state
coords = list(zip(blinkit['lat'], blinkit['lng']))
geo    = rg.search(coords, verbose=False)
blinkit['raw_city']   = [r['name']   for r in geo]
blinkit['state']      = [r['admin1'] for r in geo]
blinkit['city']       = blinkit['raw_city'].apply(normalise_city)
blinkit['company']    = 'Blinkit'
blinkit['store_name'] = 'Blinkit-' + blinkit['store_id'].astype(str)
blinkit.drop(columns=['raw_city'], inplace=True)
log(f"Blinkit: {len(blinkit)} stores | {blinkit['city'].nunique()} cities")

# ── SWIGGY ───────────────────────────────────────────────────
log("Loading and geocoding Swiggy stores...")
swiggy = pd.read_csv(f"{RAW}/swiggy-darkstores.csv")
swiggy.rename(columns={'id': 'store_id', 'locality': 'store_name'}, inplace=True)

coords_s = list(zip(swiggy['lat'], swiggy['lng']))
geo_s    = rg.search(coords_s, verbose=False)
swiggy['raw_city'] = [r['name']   for r in geo_s]
swiggy['state']    = [r['admin1'] for r in geo_s]
swiggy['city']     = swiggy['raw_city'].apply(normalise_city)
swiggy['company']  = 'Swiggy Instamart'
swiggy.drop(columns=['raw_city'], inplace=True)
log(f"Swiggy: {len(swiggy)} stores | {swiggy['city'].nunique()} cities")

# ── ZEPTO ────────────────────────────────────────────────────
log("Loading Zepto stores...")
zepto = pd.read_csv(f"{RAW}/zepto-darkstores.csv")
# Drop test/invalid rows
zepto = zepto[zepto['city'] != 'Test City'].copy()
zepto.rename(columns={'id': 'store_id', 'name': 'store_name'}, inplace=True)
zepto['company'] = 'Zepto'

# Zepto already has city names — just normalise them
zepto['state'] = zepto.get('state', 'Unknown')
zepto['city']  = zepto['city'].apply(normalise_city)
log(f"Zepto: {len(zepto)} stores | {zepto['city'].nunique()} cities")

# ── COMBINE ──────────────────────────────────────────────────
combined = pd.concat([
    blinkit.reindex(columns=FINAL_COLS),
    swiggy.reindex(columns=FINAL_COLS),
    zepto.reindex(columns=FINAL_COLS),
], ignore_index=True)

# Remove out-of-India coordinates (sanity check)
before = len(combined)
combined = combined[
    combined['lat'].between(6, 37) &
    combined['lng'].between(68, 98)
].copy()
log(f"\nOut-of-India coordinates removed: {before - len(combined)}")

log(f"\nCombined dark stores: {combined.shape}")
log(combined['company'].value_counts().to_string())
log(f"\nTop 10 cities by store count:")
log(combined['city'].value_counts().head(10).to_string())

combined.to_csv(f"{CLEAN}/dark_stores_combined.csv", index=False)
log(f"\nSaved → {CLEAN}/dark_stores_combined.csv")


# ================================================================
# SECTION 4: India Census 2011 (District-level Urban data)
# ================================================================
section("4. INDIA CENSUS 2011")

census = pd.read_excel(f"{RAW}/2011-IndiaStateDist-0000.xlsx")
log(f"Raw shape: {census.shape}")

# Keep only district-level urban rows
# (quick commerce operates in urban areas — district is the right granularity)
census_clean = census[
    (census['Level'] == 'DISTRICT') &
    (census['TRU']   == 'Urban')
].copy()
log(f"After filter (District + Urban): {census_clean.shape}")

# Keep analytically useful columns only
KEEP = ['State', 'District', 'Name', 'TOT_P', 'No_HH',
        'P_LIT', 'P_ILL', 'TOT_WORK_P', 'MAIN_OT_P', 'NON_WORK_P']
census_clean = census_clean[KEEP].copy()

# Rename for clarity
census_clean.rename(columns={
    'State'      : 'state_code',
    'District'   : 'district_code',
    'Name'       : 'district_name',
    'TOT_P'      : 'urban_population',
    'No_HH'      : 'households',
    'P_LIT'      : 'literate_pop',
    'P_ILL'      : 'illiterate_pop',
    'TOT_WORK_P' : 'total_workers',
    'MAIN_OT_P'  : 'service_workers',
    'NON_WORK_P' : 'non_workers',
}, inplace=True)

# Derive useful metrics
census_clean['literacy_rate'] = (
    census_clean['literate_pop'] / census_clean['urban_population'] * 100
).round(2)

census_clean['avg_household_size'] = (
    census_clean['urban_population'] / census_clean['households']
).round(2)

census_clean['district_name'] = (
    census_clean['district_name'].str.title().str.strip()
)

# Drop rows with null key columns
census_clean.dropna(subset=['urban_population', 'households'], inplace=True)

log(f"\nFinal shape: {census_clean.shape}")
log(f"\nTop 5 districts by urban population:")
log(census_clean.nlargest(5, 'urban_population')
    [['district_name', 'urban_population', 'households', 'literacy_rate']]
    .to_string(index=False))

census_clean.to_csv(f"{CLEAN}/india_census_urban.csv", index=False)
log(f"\nSaved → {CLEAN}/india_census_urban.csv")


# ================================================================
# SUMMARY
# ================================================================
section("CLEANING COMPLETE — SUMMARY")

log(f"{'File':<45} {'Rows':>8}")
log("-" * 55)
for f in sorted(os.listdir(CLEAN)):
    if f.endswith('.csv'):
        rows = sum(1 for _ in open(f"{CLEAN}/{f}")) - 1
        log(f"  {f:<43} {rows:>8,}")

log(f"\nCleaning completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
log("\nNext step: Load all 4 CSVs into PostgreSQL via pgAdmin")
log("  See: sql/m1_executive_kpis.sql → STEP 0 for CREATE TABLE statements")

# Save cleaning log
with open(f"{CLEAN}/cleaning_report.txt", "w") as fh:
    fh.write("\n".join(log_lines))
log(f"\nLog saved → {CLEAN}/cleaning_report.txt")
