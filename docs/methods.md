# Methods

Shift Signal has two separate routes. The planner is arithmetic on your assumptions. The historical comparison estimates what changed from data. Neither is a demand model.

## 1. Launch planner (before launch)

**Inputs.** Incumbent items with baseline units `Q_i`, price `P_i`, variable unit cost `V_i` and overlap weight `w_i`; a launch with expected units `Q_new`, price `P_new`, variable cost `V_new`, an assumed cannibalization share `c` and a total incremental launch cost `F`. All quantities refer to the same planning period.

**Displaced units.** `D = Q_new × c`. The rest, `Q_new − D`, is new to the portfolio. It combines competitor switching and category expansion; own-sales data cannot separate the two.

**Allocation.** `D` is shared across incumbents in proportion to `Q_i × w_i`. An item can never lose more than its baseline units: when one runs out, its remaining share is redistributed across the other eligible items. If `D` exceeds the total units of items with a positive weight, the scenario is rejected rather than silently capped.

**Contribution change.**

```
ΔC = Q_new (P_new − V_new) − Σ D_i (P_i − V_i) − F
```

Revenue change is the same without costs. Cannibalization is not automatically bad: displacing low-margin or loss-making units can raise contribution.

**Sensitivity.** The app recomputes `ΔC` for launch volume at 75%, 100% and 125% of plan and cannibalization from 0% to 100% in 5-point steps, with prices and costs fixed. Infeasible combinations are left out. These are scenarios, not confidence intervals.

**What it does not do.** It does not estimate demand, price elasticity, customer traffic, capacity limits or how a price change would alter the entered volume. One displaced incumbent unit is assumed per cannibalized launch unit.

## 2. Historical launch comparison (after launch)

**Design.** A balanced panel of test locations (which received the launch item on one common date) and control locations (which never offered it), with at least 4 pre- and 4 post-launch periods and at least 4 locations per group.

**Estimator: equal-location difference-in-differences.** For every location and item, take the mean per period before and after launch. Average locations equally within each group. For item `i`:

```
Δ_i = (ȳ_T,post,i − ȳ_T,pre,i) − (ȳ_C,post,i − ȳ_C,pre,i)
```

Multiply by (test locations × post periods) to report a total effect over the treated post-launch window. This is done separately for units, revenue (`units × price`) and contribution (`units × (price − unit_cost)`). The total launch cost you enter is deducted once from the portfolio contribution effect, not from item effects.

**Net displacement.** `−Σ Δ_i` over incumbents, in units. The net displacement rate divides it by the launch item's estimated units (its untreated sales are structurally zero in this design). Gains and losses among incumbents offset, so the rate can be below 0% (an estimated halo) or above 100% (wider decline or confounding). It is not clipped and is not an observed switching fraction.

**Uncertainty: location bootstrap.** 2,000 draws by default (200 to 5,000 allowed) with a fixed seed (20261002). Each draw resamples whole locations with replacement within each group, keeping every period and item of a location together, which respects serial correlation within locations (Bertrand, Duflo and Mullainathan, 2004). Intervals are 95% percentile intervals. The rate interval is withheld when more than 5% of draws have no positive launch volume.

**Diagnostic: split-pre placebo.** The pre-launch period is split into an early and a late half. For incumbents only, the late-minus-early change in units per location-period is compared between test and control, with its own bootstrap interval. An interval that excludes zero means the groups were already drifting apart before launch. An interval that includes zero does not prove parallel trends.

**Warnings the app adds.** Fewer than 10 locations in a group; a placebo interval that excludes zero; a negative additive counterfactual for an incumbent; a negative net displacement rate (halo) or one above 100%; and a withheld rate interval.

**Interpretation.** The comparison is associational. It supports a causal reading only if untreated trends would have been parallel, locations are independent, there are no spillovers or anticipation, and nothing else changed differently between the groups. The intervals cover location sampling variation conditional on the design; they do not include confounding, model bias, future demand or uncertainty in the costs you entered.

## Evidence pack

Each route exports a ZIP with `evidence.json` (version, settings, input SHA-256, summary, warnings, audit, placebo, sources and limits), `inputs.csv` and the result tables. Text that starts with `=`, `+`, `-`, `@`, a tab or a carriage return is prefixed with an apostrophe in exported CSV files.
