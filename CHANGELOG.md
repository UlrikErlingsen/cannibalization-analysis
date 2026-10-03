# Changelog

All notable changes to Shift Signal are documented here.

## [1.1.0] - 2026-10-03

Larger datasets for large retailers and restaurant groups. Methods, estimates and the evidence-pack schema are unchanged; on both fictional demos every estimate and interval is identical to 1.0.0.

### Changed

- Larger datasets: uploads up to 1000 MB (was 20 MB) and panels up to 5,000,000 date × location × item rows (was 250,000). One `MAX_ROWS` constant serves the reader and the panel validation, and `MAX_UPLOAD_MB` drives the in-code byte check; `.streamlit/config.toml`, both launchers and the Docker image default to the same 1000 MB.
- CSV files are read with pandas' fast C parser after sniffing the delimiter from the header line (comma and semicolon files read as before), and parsing stops one row past the row limit. A 5,000,000-row, 250 MB panel reads in about 2 s.
- Panel validation parses each distinct date and cleans each distinct label once, and checks duplicate cells on integer codes; the period series no longer copies the whole panel. The location bootstrap computes blocks of draws as resampling counts times the location-level arrays (same draws, same seed), so thousands of locations stay fast. A 5,000,000-row analysis with 1,000 locations, 50 items and 2,000 draws takes about 8 s at about 1.7 GB peak memory.
- Evidence packs copy `inputs.csv` up to 250,000 rows. A larger input is not copied: `evidence.json` records `input_rows`, an `inputs_note` and the SHA-256 of the loaded table (computed in chunks; same definition as before), so the pack stays small.
- The app parses an uploaded panel once and reuses it across reruns (it was re-read and re-serialized on every widget change), and builds the evidence pack once per analysis and settings.
- `run_app.bat` and `run_app.command` honor `SHIFTSIGNAL_MAX_UPLOAD_MB` (default 1000); the Dockerfile sets `STREAMLIT_SERVER_MAX_UPLOAD_SIZE=1000`.

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
