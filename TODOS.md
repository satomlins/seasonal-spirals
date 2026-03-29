# TODOS

## PyPI Publication

- **Priority:** P0
  Register the project at pypi.org and configure GitHub as a Trusted Publisher (OIDC) before tagging v0.1.0.
  Steps: pypi.org → Add Project → Add Publisher → Owner: satomlins, Repo: seasonal-spirals, Workflow: publish.yml, Environment: pypi

- **Priority:** P0
  Verify TestPyPI install with a `.dev1` pre-release before tagging `v0.1.0`.
  Run: `uv build && uv publish --index-url https://test.pypi.org/legacy/` (bump version to `0.1.0.dev1` first, then revert)

## Phase 2 — Gallery + Docs Site

- **Priority:** P1
  Set up MkDocs Material site with `mkdocstrings[python]` for API reference auto-generation.

- **Priority:** P1
  Add 5 real-world example spirals: Wikipedia pageviews (flu, COVID, Christmas), CDC/WHO ILI data, NOAA/Berkeley Earth climate anomalies.

- **Priority:** P2
  Add conda-forge recipe after PyPI is stable and there is user demand.

## Colour Scale Tuning

- **Priority:** P1
  Auto-tune `cutoff_n` / `cutoff_percentile` based on number of years (or total data points). With only 2-3 years of data the default cutoff tends to fall too high, leaving most tiles in the muted linear range and the spike colours barely visible. Need to profile across 1, 3, 5, 10-year datasets and find a formula (or lookup table) that keeps visual contrast consistent. Could be as simple as scaling `cutoff_n` inversely with `n_years`, or computing the cutoff from a quantile of the full distribution regardless of span.

## Sparse and Non-Daily Data

- **Priority:** P1
  Document and test behaviour when not every date has a value. Currently `dropna()` removes gaps silently, so tiles simply don't appear. Edge cases to cover:
  - Large gaps (e.g. months of missing data): visually empty arcs in the spiral — is this confusing or fine?
  - Weekly or monthly input: multiple weeks map to the same arc slot, later writes overwrite earlier ones. No error raised. Should we warn, aggregate, or document?
  - Sub-daily input (e.g. hourly): `.normalize()` groups all readings from the same day to the same tile slot, and only the last one in iteration order is drawn. Same silent-overwrite issue.
  - Single data point: `vmin == vmax`, which breaks `HybridNorm` (division by zero in linear segment). Needs a guard.
  - All values identical: same `vmin == vmax` issue.
  - Very short ranges (< 1 week, < 1 month): confirm no crash, check visual output makes sense.

## Known Limitations (v0.1.0)

- **Priority:** P2
  N_WEEKS=52 means Dec 31 (and Dec 30 in leap years) is silently clamped to week 51 and drawn over existing tiles. Design decision — document in API docs.

- **Priority:** P2
  Hybrid colour scheme (WikiSpiral) is designed for positive count data. All-negative data (temperature anomalies, financial returns) produces misleading colours. Users should pass `cmap=` explicitly for negative data.

- **Priority:** P3
  `tile_geometry` is exported but has no input validation — negative `day_offset` produces negative angles with no error. Add precondition assertion or document.

## Completed

