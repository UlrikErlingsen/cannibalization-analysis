# Changelog

All notable changes to Shift Signal are documented here.

## [1.0.0] - 2026-10-03

First public release.

### Added

- **Launch planner:** source-of-volume accounting for up to 100 incumbent items. Displaced units are allocated by units × overlap weight with saturation and redistribution; infeasible scenarios are rejected, not capped. Shows a source-of-volume flow, a contribution bridge, item-level substitution and a volume (±25%) × cannibalization (0–100%) sensitivity grid.
- **Launch evidence:** equal-location difference-in-differences on a complete daily or weekly test/control panel with one common launch date, for units, revenue and contribution, item by item and for the portfolio. Net displacement and its rate are reported unclipped.
- 95% location-bootstrap percentile intervals (2,000 draws, fixed seed) that resample whole locations within each group, a split-pre placebo, and design warnings for few locations, pre-launch divergence, negative counterfactuals, halo and above-100% rates.
- Panel validation with actionable messages: completeness, calendar spacing, stable groups, minimum periods and locations, and no launch-item sales before launch or in controls.
- Restaurant-menu and product-portfolio wording with deterministic fictional demos for both routes; CSV templates on the Data guide page.
- ZIP evidence packs with `evidence.json` (settings, input SHA-256, estimates, warnings, audit, placebo, sources, limits), `inputs.csv` and result tables, with spreadsheet-formula neutralisation.
- Research & limits page with verified sources and interpretation boundaries.
- Signal Hub entry point `shiftsignal.ui.render()` with `APP_INFO`, `shift:`-namespaced keys and Hub mode (no file writes, no network calls, opens on the fictional demo).
- Windows and macOS launchers (port 8596, 20 MB uploads), Dockerfile, `AI_ANALYST.md`, data guide, methods and sources documentation.
