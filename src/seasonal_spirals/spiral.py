"""
Core seasonal spiral visualisation.

Layout
------
* **Angular**  - one full revolution = one calendar year, divided into 52
  weekly arc segments (~6.9° each).
* **Radial**  - 7 day-of-week sub-bands form 7 continuous spiral arms that
  coil outward together.  The radius increases linearly with each week,
  creating a true Archimedean spiral with no discrete year boundaries.
  Oldest data sits at the centre; most recent at the outside.

Each tile is one *week × day-of-week* cell rendered as a ``Wedge`` patch.
"""

from __future__ import annotations

import calendar
from typing import Optional, Union

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
from matplotlib.collections import PatchCollection


MONTH_ABBREVS = list(calendar.month_abbr[1:])
N_WEEKS = 52


class SeasonalSpiral:
    """
    Visualise time series data as a seasonal spiral chart.

    Parameters
    ----------
    data : pd.Series
        Time series with a DatetimeIndex.  Daily frequency recommended.
    cmap : str or Colormap, optional
        Colourmap.  Default ``'YlGnBu'``.
    inner_radius : float, optional
        Inner hole radius.  Default ``0.1``.
    ring_width : float, optional
        Radial growth per full revolution (one year).  Default ``1.0``.
    start_month : int, optional
        Month at 12 o'clock.  Default ``1`` (January).
    title : str, optional
        Figure title.
    vmin, vmax : float, optional
        Colour-scale limits.
    log_scale : bool, optional
        Logarithmic colour normalisation.  Default ``False``.
    week_gap : float, optional
        Fraction of each weekly slot left as angular gap.  Default ``0.06``.
    year_gap : float, optional
        Extra radial space inserted between year boundaries.  Default ``0.15``.
    """

    def __init__(
        self,
        data: pd.Series,
        cmap: Union[str, mcolors.Colormap] = "YlGnBu",
        inner_radius: float = 0.1,
        ring_width: float = 1.0,
        start_month: int = 1,
        title: Optional[str] = None,
        vmin: Optional[float] = None,
        vmax: Optional[float] = None,
        log_scale: bool = False,
        week_gap: float = 0.06,
        year_gap: float = 0.15,
    ) -> None:
        if not isinstance(data.index, pd.DatetimeIndex):
            raise TypeError("data must have a pandas DatetimeIndex")
        if not (1 <= start_month <= 12):
            raise ValueError("start_month must be between 1 and 12")

        self.data = data.dropna().sort_index()
        self.cmap = plt.get_cmap(cmap) if isinstance(cmap, str) else cmap
        self.inner_radius = inner_radius
        self.ring_width = ring_width
        self.start_month = start_month
        self.title = title
        self.week_gap = week_gap
        self.year_gap = year_gap

        # Derived spiral constants  - the week increment absorbs the year_gap
        # so that the gap is distributed smoothly (no radial discontinuity).
        self._week_increment = (ring_width + year_gap) / N_WEEKS
        self._day_band = ring_width / 7.0

        vals = self.data.values.astype(float)
        self.vmin = float(vmin) if vmin is not None else float(np.nanmin(vals))
        self.vmax = float(vmax) if vmax is not None else float(np.nanmax(vals))

        if log_scale:
            self.norm: mcolors.Normalize = mcolors.LogNorm(
                vmin=max(self.vmin, 1e-10), vmax=self.vmax
            )
        else:
            self.norm = mcolors.Normalize(vmin=self.vmin, vmax=self.vmax)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _spiral_year(self, dt: pd.Timestamp) -> int:
        if self.start_month == 1 or dt.month >= self.start_month:
            return dt.year
        return dt.year - 1

    def _year_bounds(self, sy: int) -> tuple[pd.Timestamp, pd.Timestamp]:
        start = pd.Timestamp(year=sy, month=self.start_month, day=1)
        return start, start + pd.DateOffset(years=1)

    def _build_cache(
        self, spiral_years: list[int]
    ) -> dict[int, tuple[pd.Timestamp, int]]:
        cache: dict[int, tuple[pd.Timestamp, int]] = {}
        for sy in spiral_years:
            start, end = self._year_bounds(sy)
            cache[sy] = (start, (end - start).days)
        return cache

    def _tile_geometry(
        self, day_offset: int, year_idx: int, weekday: int
    ) -> tuple[float, float, float, float]:
        """
        Return ``(arc_start_rad, arc_width_rad, r_inner, r_outer)`` for a
        single day tile on a continuous Archimedean spiral.

        * Angular position determined by **week number** (0–51).
        * Radial sub-band determined by **weekday** (0 = Monday at the
          inner edge, 6 = Sunday at the outer edge).
        """
        week_num = min(day_offset // 7, N_WEEKS - 1)

        # Angular: week slot
        slot_rad = 2.0 * np.pi / N_WEEKS
        arc_width = slot_rad * (1.0 - self.week_gap)
        arc_start = week_num * slot_rad

        # Radial: continuous spiral  - year_gap is baked into _week_increment
        # so it distributes smoothly with no discontinuity at the seam.
        total_weeks = year_idx * N_WEEKS + week_num
        base_r = self.inner_radius + total_weeks * self._week_increment
        r_inner = base_r + weekday * self._day_band
        r_outer = r_inner + self._day_band

        return float(arc_start), float(arc_width), float(r_inner), float(r_outer)

    @staticmethod
    def _to_mpl_angle(theta_rad: float) -> float:
        """Clockwise-from-North (rad) → matplotlib CCW-from-East (deg)."""
        return 90.0 - np.degrees(theta_rad)

    def _polar_to_xy(self, r: float, theta_rad: float) -> tuple[float, float]:
        """Clockwise-from-North polar → Cartesian."""
        return r * np.sin(theta_rad), r * np.cos(theta_rad)

    def _month_angles(self, sy: int, year_start: pd.Timestamp) -> list[tuple[float, str]]:
        results: list[tuple[float, str]] = []
        for m in range(12):
            month_num = (self.start_month - 1 + m) % 12 + 1
            cal_year = sy if month_num >= self.start_month else sy + 1
            ts = pd.Timestamp(year=cal_year, month=month_num, day=1)
            if ts >= year_start + pd.DateOffset(years=1):
                continue
            day_off = (ts - year_start).days
            week_num = min(day_off // 7, N_WEEKS - 1)
            angle = week_num * (2.0 * np.pi / N_WEEKS)
            results.append((angle, MONTH_ABBREVS[month_num - 1]))
        return results

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def plot(
        self,
        ax: Optional[plt.Axes] = None,
        figsize: tuple[float, float] = (9, 9),
        show_month_labels: bool = True,
        show_year_labels: bool = True,
        month_label_size: float = 9.0,
        year_label_size: float = 7.5,
        colourbar: bool = True,
        colourbar_label: Optional[str] = None,
    ) -> tuple[plt.Figure, plt.Axes]:
        """Render the seasonal spiral."""
        if ax is None:
            fig, ax = plt.subplots(figsize=figsize)
        else:
            fig = ax.figure

        ax.set_aspect("equal")
        ax.axis("off")

        # Year metadata
        spiral_years = sorted(
            set(self._spiral_year(dt) for dt in self.data.index)
        )
        min_year = spiral_years[0]
        n_years = len(spiral_years)
        cache = self._build_cache(spiral_years)

        # Build Wedge patches
        patches: list[mpatches.Wedge] = []
        rgba: list[tuple] = []

        for dt, value in self.data.items():
            sy = self._spiral_year(dt)
            year_start, _ = cache[sy]
            year_idx = sy - min_year
            day_offset = (dt.normalize() - year_start).days
            # Monday = 0 (inner) … Sunday = 6 (outer)
            weekday = dt.weekday()

            arc_start, arc_width, r_inner, r_outer = self._tile_geometry(
                day_offset, year_idx, weekday
            )
            arc_end = arc_start + arc_width

            theta1 = self._to_mpl_angle(arc_end)
            theta2 = self._to_mpl_angle(arc_start)

            patches.append(
                mpatches.Wedge(
                    center=(0.0, 0.0),
                    r=r_outer,
                    theta1=theta1,
                    theta2=theta2,
                    width=r_outer - r_inner,
                )
            )
            rgba.append(self.cmap(self.norm(float(value))))

        collection = PatchCollection(patches, linewidth=0, antialiased=True)
        collection.set_facecolors(rgba)
        ax.add_collection(collection)

        outer_r = (self.inner_radius
                   + n_years * N_WEEKS * self._week_increment
                   + 6 * self._day_band)

        # Month labels
        if show_month_labels:
            max_sy = spiral_years[-1]
            year_start, _ = cache[max_sy]
            label_r = outer_r + 0.3
            for angle, abbrev in self._month_angles(max_sy, year_start):
                x, y = self._polar_to_xy(label_r, angle)
                ax.text(
                    x, y, abbrev,
                    ha="center", va="center",
                    fontsize=month_label_size, color="#444444",
                )

        # Year labels
        if show_year_labels:
            label_theta = np.deg2rad(4)
            for i, sy in enumerate(spiral_years):
                r_c = (self.inner_radius
                       + (i * N_WEEKS + N_WEEKS // 2) * self._week_increment
                       + 3 * self._day_band)
                x, y = self._polar_to_xy(r_c, label_theta)
                ax.text(
                    x, y, str(sy),
                    ha="left", va="center",
                    fontsize=year_label_size,
                    color="black", fontweight="bold", zorder=5,
                )

        # Axis limits
        margin = 0.5
        lim = outer_r + margin
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)

        if self.title:
            fig.suptitle(self.title, fontsize=13, y=0.98)

        if colourbar:
            sm = plt.cm.ScalarMappable(norm=self.norm, cmap=self.cmap)
            sm.set_array([])
            cbar = fig.colorbar(sm, ax=ax, shrink=0.5, pad=0.05, aspect=25)
            if colourbar_label:
                cbar.set_label(colourbar_label)

        fig.tight_layout()
        return fig, ax


def plot_spiral(
    data: pd.Series,
    *,
    cmap: Union[str, mcolors.Colormap] = "YlGnBu",
    inner_radius: float = 0.1,
    ring_width: float = 1.0,
    start_month: int = 1,
    title: Optional[str] = None,
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
    log_scale: bool = False,
    week_gap: float = 0.06,
    year_gap: float = 0.15,
    figsize: tuple[float, float] = (9, 9),
    show_month_labels: bool = True,
    show_year_labels: bool = True,
    colourbar: bool = True,
    colourbar_label: Optional[str] = None,
) -> tuple[plt.Figure, plt.Axes]:
    """Create a seasonal spiral chart in a single call."""
    spiral = SeasonalSpiral(
        data,
        cmap=cmap,
        inner_radius=inner_radius,
        ring_width=ring_width,
        start_month=start_month,
        title=title,
        vmin=vmin,
        vmax=vmax,
        log_scale=log_scale,
        week_gap=week_gap,
        year_gap=year_gap,
    )
    return spiral.plot(
        figsize=figsize,
        show_month_labels=show_month_labels,
        show_year_labels=show_year_labels,
        colourbar=colourbar,
        colourbar_label=colourbar_label,
    )
