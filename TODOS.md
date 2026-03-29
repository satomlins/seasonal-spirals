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

## Known Limitations (v0.1.0)

- **Priority:** P2
  N_WEEKS=52 means Dec 31 (and Dec 30 in leap years) is silently clamped to week 51 and drawn over existing tiles. Design decision — document in API docs.

- **Priority:** P2
  Hybrid colour scheme (WikiSpiral) is designed for positive count data. All-negative data (temperature anomalies, financial returns) produces misleading colours. Users should pass `cmap=` explicitly for negative data.

- **Priority:** P3
  `tile_geometry` is exported but has no input validation — negative `day_offset` produces negative angles with no error. Add precondition assertion or document.

## Completed

