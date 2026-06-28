Business Question

Which cities should each company prioritise for new dark store openings — and where are they completely absent from the market?

The composite expansion score addresses this by combining 4 signals:

SignalWeightWhat it measuresOpportunity score40%Households × literacy ÷ current storesCoverage gap30%How thin is our store density vs city size?White-space urgency20%Are we completely absent (0 stores)?Competitive gap10%How far behind the market leader are we?

Each signal is min-max normalised to 0–1 before weighting so no single metric dominates due to its raw scale.


Key Design Decisions:

Households (not urban population) as the demand numerator — Quick commerce is ordered by household, not by individual. A household of 4 generates roughly 1 order, not 4. Households is the correct proxy for addressable demand.

Per-company store count in the denominator (not total market) — Each company's opportunity is independent of its rivals. Blinkit having 0 stores in a city is a Blinkit-specific opportunity, regardless of how many Zepto stores are there.

+1 in the denominator — Prevents division by zero for cities with 0 current stores. Also models the marginal opportunity of the next store to open.
