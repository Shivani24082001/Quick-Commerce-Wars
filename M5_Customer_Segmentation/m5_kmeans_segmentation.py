# ================================================================
# Quick Commerce Wars
# Module 5: Customer Segmentation — K-Means Clustering
# ================================================================
# Author  : [Your Name]
# Tool    : Google Colab (Python 3.10+)
#
# Purpose : Segment ~375K orders into 4 behavioural clusters
#           using K-Means. Validate k=4 with elbow method and
#           silhouette score. Visualise using PCA 2D projection.
#
# Why K-Means (not RFM)?
#   RFM (Recency/Frequency/Monetary) requires customer IDs and
#   timestamps — neither exists in this dataset in a usable form.
#   K-Means on order-level features produces equivalent business
#   segments without requiring longitudinal customer tracking.
#
# Features used (6):
#   order_value, customer_rating, is_discounted,
#   distance_km, delivery_time_min, customer_age
#
#
# ================================================================

import pandas as pd
import numpy as np
import os
import warnings
warnings.filterwarnings('ignore')

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA

# ── Paths ────────────────────────────────────────────────────
CLEAN  = "/content/drive/MyDrive/QuickCommerceWars/data/cleaned"
M5OUT  = "/content/drive/MyDrive/QuickCommerceWars/data/m5_outputs"
os.makedirs(M5OUT, exist_ok=True)


# ================================================================
# CELL 1: Load data
# ================================================================
# You can load either the SQL feature export or the cleaned CSV.
# Both contain the same 6 features. The cleaned CSV is used here

df = pd.read_csv(f"{CLEAN}/qc_main_cleaned.csv")

print("=== DATA LOADED ===")
print(f"Shape: {df.shape}")
print(f"\nCompany counts:")
print(df['company'].value_counts().to_string())

FEATURES = [
    'order_value',
    'customer_rating',
    'is_discounted',
    'distance_km',
    'delivery_time_min',
    'customer_age',
]

print(f"\nFeatures for clustering: {FEATURES}")
print(f"\nNull counts in features:")
print(df[FEATURES].isnull().sum().to_string())


# ================================================================
# CELL 2: Prepare features and scale
# ================================================================

df_clean = df[['order_id', 'company', 'city', 'product_category'] + FEATURES].dropna()
print(f"\n=== FEATURE SCALING ===")
print(f"Rows after dropping nulls: {len(df_clean):,}  (from {len(df):,})")

X        = df_clean[FEATURES].values
scaler   = StandardScaler()
X_scaled = scaler.fit_transform(X)

print(f"Scaled shape: {X_scaled.shape}")
print(f"\nPre-scaling feature ranges:")
for i, feat in enumerate(FEATURES):
    print(f"  {feat:<22}: {X[:, i].min():.1f} – {X[:, i].max():.1f}")

print(f"\nPost-scaling feature ranges (should be ~-3 to +3):")
for i, feat in enumerate(FEATURES):
    print(f"  {feat:<22}: {X_scaled[:, i].min():.2f} – {X_scaled[:, i].max():.2f}")


# ================================================================
# CELL 3: Elbow Method — choose optimal k
# ================================================================

print("\n=== ELBOW METHOD (k=2 to 8) ===")
print("This will take 5–8 minutes. One line per k...\n")

elbow_results = []

for k in range(2, 9):
    km = KMeans(
        n_clusters   = k,
        init         = 'k-means++',   # smarter initialisation than random
        n_init       = 5,             # 5 initialisations, picks best
        random_state = 42,
        max_iter     = 200,
    )
    km.fit(X_scaled)
    elbow_results.append({
        'k'      : k,
        'inertia': round(km.inertia_, 2),
    })
    print(f"  k={k}  inertia={km.inertia_:,.0f}")

elbow_df = pd.DataFrame(elbow_results)
elbow_df.to_csv(f"{M5OUT}/m5_elbow_scores.csv", index=False)
print(f"\nSaved ✓  → m5_elbow_scores.csv")
print("Tableau: Line chart — k on X, inertia on Y. Elbow = optimal k.")


# ================================================================
# CELL 4: Silhouette Score — validate cluster separation
# ================================================================

print("\n=== SILHOUETTE SCORES (10,000 row sample) ===")

sample_idx = np.random.RandomState(42).choice(len(X_scaled), 10000, replace=False)
X_sample   = X_scaled[sample_idx]

sil_results = []

for k in range(2, 7):
    km     = KMeans(n_clusters=k, init='k-means++',
                    n_init=5, random_state=42)
    labels = km.fit_predict(X_sample)
    score  = silhouette_score(X_sample, labels)
    sil_results.append({'k': k, 'silhouette_score': round(score, 4)})
    print(f"  k={k}  silhouette={score:.4f}")

sil_df  = pd.DataFrame(sil_results)
best_k  = int(sil_df.loc[sil_df['silhouette_score'].idxmax(), 'k'])
sil_df.to_csv(f"{M5OUT}/m5_silhouette_scores.csv", index=False)

print(f"\nBest k by silhouette: {best_k}")
print(f"Proceeding with k=4 for business interpretability.")
print(f"(Silhouette identifies statistical optimum; k=4 maps cleanly")
print(f" to 4 business segments: Champions, Loyals, Price-Sensitive, At-Risk)")
print(f"\nSaved ✓  → m5_silhouette_scores.csv")


# ================================================================
# CELL 5: Final K-Means — k=4
# ================================================================

K = 4
print(f"\n=== FINAL K-MEANS CLUSTERING (k={K}) ===")

km_final = KMeans(
    n_clusters   = K,
    init         = 'k-means++',
    n_init       = 10,              # more initialisations for final run
    random_state = 42,
    max_iter     = 300,
)

df_clean = df_clean.copy()
df_clean['cluster'] = km_final.fit_predict(X_scaled)

print(f"\nCluster sizes:")
print(df_clean['cluster'].value_counts().sort_index().to_string())

# Cluster centres in original scale (inverse transform)
centres = pd.DataFrame(
    scaler.inverse_transform(km_final.cluster_centers_),
    columns=FEATURES
).round(2)
centres.index.name = 'cluster'
centres = centres.reset_index()

print(f"\n=== CLUSTER CENTRES (original scale) ===")
print(centres.to_string(index=False))
print("\nRead the centre values above carefully before running Cell 6.")
print("The cluster numbers (0,1,2,3) are randomly assigned by K-Means.")
print("You need to match centre values to segment names manually.")


# ================================================================
# CELL 6: Label clusters with business segment names
# ================================================================

def label_cluster(row):
    """
    Assign a business segment name based on cluster centre values.
    Adjust thresholds if your cluster centres look different.
    """
    ov  = row['order_value']
    cr  = row['customer_rating']
    dis = row['is_discounted']

    if ov >= 600 and cr >= 3.8:
        return 'Champions'
    elif ov >= 400 and cr >= 3.5 and dis < 0.5:
        return 'Loyals'
    elif dis >= 0.5 and cr < 3.5:
        return 'At-Risk'
    else:
        return 'Price-Sensitive'

centres['segment_label'] = centres.apply(label_cluster, axis=1)

print("=== CLUSTER LABELS ===")
print(centres[['cluster', 'segment_label', 'order_value',
               'customer_rating', 'is_discounted']].to_string(index=False))

# Check for duplicate labels (two clusters with same name = bad thresholds)
if centres['segment_label'].nunique() < K:
    print("\n⚠  WARNING: Duplicate segment labels detected.")
    print("   Adjust the thresholds in label_cluster() to match YOUR centres.")
else:
    print(f"\n✓  All {K} clusters have unique segment labels")

# Map labels back to the main dataframe
cluster_to_label = centres.set_index('cluster')['segment_label'].to_dict()
df_clean['segment_label'] = df_clean['cluster'].map(cluster_to_label)


# ================================================================
# CELL 7: Cluster profile table
# ================================================================

profiles = df_clean.groupby('segment_label')[FEATURES].mean().round(2).reset_index()
profiles['order_count'] = df_clean.groupby('segment_label')['order_id'].count().values
profiles['share_pct']   = (profiles['order_count'] / len(df_clean) * 100).round(1)

print("=== SEGMENT PROFILES ===")
print(profiles.to_string(index=False))

profiles.to_csv(f"{M5OUT}/m5_cluster_profiles.csv", index=False)
print(f"\nSaved ✓  → m5_cluster_profiles.csv")
print("Tableau: Heatmap — segment on rows, features on columns, value as colour")


# ================================================================
# CELL 8: Save labelled orders + segment per company breakdown
# ================================================================

# Full labelled dataset — load this back into PostgreSQL for SQL Query 2
clustered_out = df_clean[['order_id', 'company', 'city',
                           'cluster', 'segment_label']].copy()
clustered_out.to_csv(f"{M5OUT}/m5_clustered_orders.csv", index=False)
print(f"Saved ✓  → m5_clustered_orders.csv ({len(clustered_out):,} rows)")
print("Next: Load this into PostgreSQL → run SQL Query 2 for segment distribution")

# Segment distribution per company (Python version — matches SQL Query 2)
seg_company = (
    df_clean.groupby(['company', 'segment_label'])
    .size()
    .reset_index(name='orders')
)
seg_company['pct_of_company'] = (
    seg_company.groupby('company')['orders']
    .transform(lambda x: x / x.sum() * 100)
).round(2)

print(f"\n=== SEGMENT DISTRIBUTION PER COMPANY ===")
print(seg_company.sort_values(['company', 'orders'], ascending=[True, False])
      .to_string(index=False))

seg_company.to_csv(f"{M5OUT}/m5_segment_company.csv", index=False)
print(f"\nSaved ✓  → m5_segment_company.csv")


# ================================================================
# CELL 9: PCA 2D Scatter — visualise clusters
# ================================================================
# PCA reduces the 6 clustering features to 2 principal components
# that capture the most variance. The 2D scatter shows whether
# clusters are visually separated or overlapping.
# Uses a 5,000 row sample — plotting all 375K points is too slow.

print("\n=== PCA 2D PROJECTION (5,000 row sample) ===")

sample_idx = np.random.RandomState(42).choice(len(X_scaled), 5000, replace=False)
X_pca_in   = X_scaled[sample_idx]

pca        = PCA(n_components=2, random_state=42)
X_pca      = pca.fit_transform(X_pca_in)

pca_df = pd.DataFrame({
    'pca_x'        : X_pca[:, 0].round(4),
    'pca_y'        : X_pca[:, 1].round(4),
    'cluster'      : df_clean.iloc[sample_idx]['cluster'].values,
    'segment_label': df_clean.iloc[sample_idx]['segment_label'].values,
    'order_value'  : df_clean.iloc[sample_idx]['order_value'].values,
    'company'      : df_clean.iloc[sample_idx]['company'].values,
})

print(f"Variance explained by PC1: {pca.explained_variance_ratio_[0] * 100:.1f}%")
print(f"Variance explained by PC2: {pca.explained_variance_ratio_[1] * 100:.1f}%")
print(f"Total variance captured  : {pca.explained_variance_ratio_.sum() * 100:.1f}%")
print(f"\nSample points per segment:")
print(pca_df['segment_label'].value_counts().to_string())

pca_df.to_csv(f"{M5OUT}/m5_pca_scatter.csv", index=False)
print(f"\nSaved ✓  → m5_pca_scatter.csv")
print("Tableau: Scatter plot — pca_x on X, pca_y on Y, segment_label as colour")
print("         Size = order_value, Opacity = 60%")


# ================================================================
# CELL 10: Output checklist
# ================================================================

SQL_FILES = [
    ("m5_features_for_clustering.csv", "~375K rows", "SQL Query 1 (input to this script)"),
    ("m5_segment_distribution.csv",    "~12 rows",   "SQL Query 2 (run after loading clustered_orders)"),
]
PY_FILES = [
    ("m5_elbow_scores.csv",            "7 rows",     "Cell 3"),
    ("m5_silhouette_scores.csv",       "5 rows",     "Cell 4"),
    ("m5_cluster_profiles.csv",        "4 rows",     "Cell 7"),
    ("m5_clustered_orders.csv",        "~375K rows", "Cell 8 — load into PostgreSQL"),
    ("m5_segment_company.csv",         "~12 rows",   "Cell 8"),
    ("m5_pca_scatter.csv",             "5K rows",    "Cell 9"),
]

print("\n=== OUTPUT FILE CHECKLIST ===")
print("\nSQL exports / inputs:")
for fname, rows, source in SQL_FILES:
    exists = "✓" if os.path.exists(f"{M5OUT}/{fname}") else "✗ missing"
    print(f"  {exists}  {fname:<45} {rows:<12} {source}")

print("\nPython outputs (this script):")
for fname, rows, source in PY_FILES:
    exists = "✓" if os.path.exists(f"{M5OUT}/{fname}") else "✗ missing"
    print(f"  {exists}  {fname:<45} {rows:<12} {source}")

print("\nWorkbook name  : Quick-Commerce-Wars-M5")
print("Dashboard name : M5 Customer Segmentation")
print("\nDashboard layout:")
print("  Row 1: Elbow curve | Silhouette scores")
print("  Row 2: Segment distribution (stacked bar) | PCA scatter")
print("  Row 3: Segment profiles heatmap (full width)")
