# Changelog

All notable changes to Shift Signal are documented here.

## [1.1.0] - 2026-10-03

Larger datasets for large retailers and restaurant groups. Methods, estimates and the evidence-pack schema are unchanged; on both fictional demos every estimate and interval is identical to 1.0.0.

### Changed

- Larger datasets: run locally, Shift Signal has no built-in limit on file size, panel rows, items or bootstrap draws any more (it was 20 MB, 250,000 rows, 100 items and 5,000 draws); memory is the limit, and running out of memory is reported as a plain message. The public demo (`SIGNAL_PUBLIC=1`) keeps those values as demo limits from the new `shiftsignal/limits.py`, and its messages say the downloaded app has none.
- CSV files are read with pandas' fast C parser after sniffing the delimiter from the header line (comma and semicolon files read as before). A 5,000,000-row, 250 MB panel reads in about 2 s.
- Panel validation parses each distinct date and cleans each distinct label once, and checks duplicate cells on integer codes; the period series no longer copies the whole panel. The location bootstrap computes blocks of draws as resampling counts times the location-level arrays (same draws, same seed), so thousands of locations stay fast. A 5,000,000-row analysis with 1,000 locations, 50 items and 2,000 draws takes about 8 s at about 1.7 GB peak memory.
- Evidence packs always contain the full input table and now record `input_rows`; the input SHA-256 is computed in chunks (same definition) and spreadsheet-formula neutralisation runs once per distinct value. Above 250,000 input rows the pack is prepared on request (about 27 s for 5,000,000 rows) instead of on every page view.
- The app parses an uploaded panel once and reuses it across reruns (it was re-read and re-serialized on every widget change). The item-effect chart and the source-of-volume flow show at most 40 items with a note; tables and exports hold every item.
- Streamlit's upload cap is 10,000 MB: `.streamlit/config.toml` (synced from Signal Hub), both launchers (`SHIFTSIGNAL_MAX_UPLOAD_MB`, default 10000) and the Dockerfile (`STREAMLIT_SERVER_MAX_UPLOAD_SIZE=10000`).

### Suite

- Suite: Rival, Reach, Learn and Blueprint Signal added to the suite table.

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
