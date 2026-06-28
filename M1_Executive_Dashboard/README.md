# Module 1 — Executive Strategy Dashboard

> **Quick Commerce Wars · M1 of 7**

---

## Business Question

How do Blinkit, Zepto, and Swiggy Instamart compare on the metrics that matter most to an executive — market share, revenue, average order value, delivery speed, and customer satisfaction?

---

## What This Module Covers

| Analysis | Tool | Output file |
|---|---|---|
| Market share by order volume | SQL | `m1_market_share.csv` |
| Revenue & AOV per company | SQL | `m1_revenue_aov.csv` |
| Delivery speed (avg, P50, P90, slow rate) | SQL | `m1_delivery_kpis.csv` |
| City-level revenue breakdown | SQL | `m1_city_revenue.csv` |
| Payment method distribution | SQL | `m1_payment_methods.csv` |
| Order value tier distribution | SQL | `m1_order_value_tiers.csv` |
| Customer & partner ratings | SQL | `m1_ratings.csv` |
| Executive summary (cross-metric) | Python | `m1_executive_summary.csv` |

---


---

## Key Findings

**Zepto is the speed leader** — 9.6 min average delivery vs Blinkit 15.1 min and Swiggy 16.0 min. More importantly, Zepto's P90 delivery (worst 10% of orders) is still ~14 min. Swiggy's P90 is ~28 min. P90 is what drives churn, not the average.

**Swiggy has the highest AOV** — ₹646 vs Blinkit ₹543 and Zepto ₹489. Despite being the slowest, Swiggy attracts higher-value orders — customers spending more per trip. This makes Swiggy's revenue competitive even with fewer orders than Blinkit.

**Blinkit leads on volume** — highest order count and market share, but Zepto's speed advantage and Swiggy's AOV advantage both pose strategic threats.

**UPI dominates payments** — all three companies show UPI as the dominant payment method (~60%+), with COD as the second choice. Card payments are notably low across all platforms.

---

---

## Assumptions & Limitations

- "Slow order" is defined as delivery time > 30 minutes. This threshold is based on quick commerce industry convention (10-minute promise with 3× as the outer bound).
- Revenue figures are in INR. No currency conversion applied.
- City = 'Unknown' rows (~2% of data) are excluded from city-level queries but included in company-level totals.

