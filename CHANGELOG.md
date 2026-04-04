# Changelog

All notable changes to this project will be documented in this file.

## [0.3.0] - 2026-04-04

### Fixed
- Month labels now move to the outermost ring one week before data reaches them, preventing tiles from overlapping the label text.
- Month label ring selection and radial position are now both derived from the label's actual angular position (the 15th of the month) using ISO-week-aligned week slots, matching `tile_geometry` exactly.
- Regenerated README spiral image with corrected title (plain dash, no em-dash).

### Changed
- Dev/scratch notebooks removed from the repository (kept locally via `.gitignore`).

## [0.2.0] - 2026-03-29

### Changed (breaking)
- Default cutoff method changed from `2 * P75` to the Tukey IQR fence (`Q3 + 1.5 * IQR`). The new default is more robust: extreme outlier days do not pull the cutoff upward, so seasonal variation is consistently visible even when a topic has a handful of viral-spike days.
- `cutoff_n` and `cutoff_percentile` parameters removed from `plot_spiral`, `plot_spiral_static`, and `SeasonalSpiral`. Use `cutoff_fn` for a custom rule or `cutoff` to supply a known value directly.
- `auto_cutoff` in `_colourmap.py` no longer accepts `cutoff_n` / `cutoff_percentile` arguments.

### Added
- `cutoff_fn` parameter on all three entry points. Accepts any callable `(values: np.ndarray) -> float`. The result is clamped to `[vmin + 5%, vmax - 5%]` automatically. See README for ready-to-use examples (MAD/Hampel, log-normal, fixed percentile).

## [0.1.1] - 2026-03-29

### Changed
- British English throughout: `_colormap.py` → `_colourmap.py`, `test_colormap.py` → `test_colourmap.py`, pyproject description/keywords updated
- Public parameter `colorscale` in `plot_spiral()` intentionally kept to match Plotly's naming convention; internal variable renamed `_colourscale`
- Two new TODOS added: colour scale auto-tuning for short datasets; sparse/non-daily data edge cases

## [0.1.0] - 2026-03-29

### Added
- `_geometry.py`: shared spiral coordinate math extracted as single source of truth for both backends (`spiral_year`, `spiral_year_start`, `trim_to_max_years`, `tile_geometry`, `month_label_positions`)
- `tests/test_geometry.py`: 25 direct unit tests for all geometry functions including spiral year boundary cases, tile r_inner < r_outer, week clamping, and month label positions
- `tests/test_colourmap.py`: 20 direct unit tests for `auto_cutoff`, `HybridNorm` (boundary at cutoff, clip behaviour, log_range=0), and `WIKISPIRAL_PLOTLY` structure
- `.github/workflows/ci.yml`: CI matrix running pytest on Python 3.10, 3.11, 3.12 via `uv sync --group dev --extra matplotlib`
- `.github/workflows/publish.yml`: PyPI publish workflow on `v*` tags using OIDC Trusted Publishing (no long-lived tokens)
- `assets/spiral_influenza.png`: generated static spiral for README gallery
- PyPI badge and embedded spiral image in README

### Changed
- Both backends now import from `_geometry.py` instead of duplicating coordinate math
- Month labels in `interactive.py` use calendar-accurate `month_label_positions` instead of evenly-spaced 30° approximation
- Hover text in `interactive.py` now uses adaptive formatting: integer format for whole-number data, 3 significant figures for decimal data
- Timezone-aware `DatetimeIndex` inputs are now accepted in both backends (tz info stripped before date arithmetic — previously crashed with `TypeError`)
- `pyproject.toml`: added `authors`, `license = {file = "LICENSE"}`, `urls`, `classifiers`; widened `requires-python` from `>=3.12` to `>=3.10`; removed duplicate `[project.optional-dependencies].dev`; fixed `[dependency-groups].dev`

### Fixed
- `plot_spiral_static` default `cutoff_n` was `3.0`, inconsistent with `SeasonalSpiral` and `plot_spiral` defaults of `2.0` — now `2.0` across all three entry points
- `interactive.py` had unused `import calendar` and dead `DAY_NAMES` constant after refactor — removed
