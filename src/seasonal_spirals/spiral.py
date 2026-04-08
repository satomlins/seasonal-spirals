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

from typing import Callable, Optional, Union

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
from matplotlib.collections import PatchCollection

from seasonal_spirals._colourmap import (
    HybridNorm,
    auto_cutoff,
    make_wikispiral_mpl_cmap,
)
from seasonal_spirals._geometry import (
    N_WEEKS,
    spiral_year,
    spiral_year_start,
    trim_to_max_years,
    tile_geometry,
    month_label_positions,
)


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
    cutoff_fn : callable, optional
        Function ``(values: np.ndarray) -> float`` that computes the colour
        scale cutoff from the raw data array.  Defaults to the Tukey IQR fence
        (``Q3 + 1.5 * IQR``).  Use this to swap in a different outlier
        detection rule without touching the rest of the colour scheme.
        The result is clamped to ``[vmin + 5%, vmax - 5%]`` automatically.
    """

    def __init__(
        self,
        data: pd.Series,
        cmap: Union[str, mcolors.Colormap, None] = None,
        inner_radius: float = 0.1,
        ring_width: float = 1.0,
        start_month: int = 1,
        title: Optional[str] = None,
        vmin: Optional[float] = None,
        vmax: Optional[float] = None,
        log_scale: bool = False,
        week_gap: float = 0.06,
        year_gap: float = 0.15,
        max_years: int = 9,
        cutoff: Optional[float] = None,
        cutoff_fn: Optional[Callable[[np.ndarray], float]] = None,
    ) -> None:
        if not isinstance(data.index, pd.DatetimeIndex):
            raise TypeError("data must have a pandas DatetimeIndex")
        if not (1 <= start_month <= 12):
            raise ValueError("start_month must be between 1 and 12")
        try:
            is_numeric = np.issubdtype(data.dtype, np.number)
        except TypeError:
            is_numeric = False
        if not is_numeric:
            raise TypeError("data must contain numeric values")

        self.data = data.dropna().sort_index()
        if len(self.data) == 0:
            raise ValueError("data is empty (or all NaN)")

        # Strip timezone info if present — daily data, tz not relevant for date math
        if getattr(self.data.index, "tz", None) is not None:
            self.data.index = self.data.index.tz_localize(None)

        self.data = trim_to_max_years(self.data, start_month, max_years)

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
            # Explicit log scale: use standard matplotlib LogNorm + supplied cmap
            self.cmap = plt.get_cmap(cmap if cmap is not None else "YlGnBu") if isinstance(cmap, str) or cmap is None else cmap
            self.norm: mcolors.Normalize = mcolors.LogNorm(
                vmin=max(self.vmin, 1e-10), vmax=self.vmax
            )
            self._hybrid_norm = None
        elif cmap is not None:
            # Explicit cmap supplied: linear norm, user's cmap
            self.cmap = plt.get_cmap(cmap) if isinstance(cmap, str) else cmap
            self.norm = mcolors.Normalize(vmin=self.vmin, vmax=self.vmax)
            self._hybrid_norm = None
        else:
            # Default: WikiSpiral hybrid linear-log colour scheme
            if cutoff is not None:
                _cutoff = float(cutoff)
            elif cutoff_fn is not None:
                _raw = float(cutoff_fn(vals))
                _eps = (self.vmax - self.vmin) * 0.05
                _cutoff = float(np.clip(_raw, self.vmin + _eps, self.vmax - _eps))
            else:
                _cutoff = auto_cutoff(vals, self.vmin, self.vmax)
            self.cutoff = _cutoff
            self._hybrid_norm = HybridNorm(self.vmin, self.vmax, _cutoff)
            self.cmap = make_wikispiral_mpl_cmap()
            self.norm = mcolors.Normalize(vmin=0.0, vmax=1.0)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_mpl_angle(theta_rad: float) -> float:
        """Clockwise-from-North (rad) → matplotlib CCW-from-East (deg)."""
        return 90.0 - np.degrees(theta_rad)

    def _polar_to_xy(self, r: float, theta_rad: float) -> tuple[float, float]:
        """Clockwise-from-North polar → Cartesian."""
        return r * np.sin(theta_rad), r * np.cos(theta_rad)

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
        colourbar: bool = False,
        colourbar_label: Optional[str] = None,
        dark_mode: bool = False,
    ) -> tuple[plt.Figure, plt.Axes]:
        """Render the seasonal spiral."""
        _bg = "#0f1117" if dark_mode else "white"
        _label_color = "#e6edf3" if dark_mode else "#444444"
        _year_color = "#e6edf3" if dark_mode else "black"

        if ax is None:
            fig, ax = plt.subplots(figsize=figsize)
        else:
            fig = ax.figure

        if dark_mode:
            fig.patch.set_facecolor(_bg)
            ax.set_facecolor(_bg)

        ax.set_aspect("equal")
        ax.axis("off")

        # Year metadata
        spiral_years = sorted(
            set(spiral_year(dt, self.start_month) for dt in self.data.index)
        )
        min_year = spiral_years[0]
        n_years = len(spiral_years)

        # Build Wedge patches
        patches: list[mpatches.Wedge] = []
        rgba: list[tuple] = []

        for dt, value in self.data.items():
            sy = spiral_year(dt, self.start_month)
            year_start = spiral_year_start(sy, self.start_month)
            year_idx = sy - min_year
            day_offset = (dt.normalize() - year_start).days
            # Monday = 0 (inner) … Sunday = 6 (outer)
            weekday = dt.weekday()

            arc_start, arc_width, r_inner, r_outer = tile_geometry(
                day_offset, year_idx, weekday,
                self.inner_radius, self.ring_width, self.week_gap, self.year_gap,
                year_start_weekday=year_start.weekday(),
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
            v = float(value)
            mapped = self._hybrid_norm(np.array([v]))[0] if self._hybrid_norm is not None else self.norm(v)
            rgba.append(self.cmap(mapped))

        collection = PatchCollection(patches, linewidth=0, antialiased=True)
        collection.set_facecolors(rgba)
        ax.add_collection(collection)

        outer_r = (self.inner_radius
                   + n_years * N_WEEKS * self._week_increment
                   + 6 * self._day_band)

        # Month labels
        if show_month_labels:
            max_sy = spiral_years[-1]
            last_year_idx = max_sy - min_year
            max_sy_start = spiral_year_start(max_sy, self.start_month)
            last_dt = self.data.index[-1]
            last_day_off = (last_dt.normalize() - max_sy_start).days

            max_label_r = 0.0
            for angle, abbrev, week_num, r_label in month_label_positions(
                max_sy, max_sy_start, self.start_month,
                self.inner_radius, self.ring_width, self.year_gap,
                last_year_idx, last_day_off,
                year_start_weekday=max_sy_start.weekday(),
            ):
                max_label_r = max(max_label_r, r_label)

                angle_deg = np.degrees(angle)
                rotation = (-angle_deg) % 360
                if rotation > 180:
                    rotation -= 360
                if rotation > 90:
                    rotation -= 180
                elif rotation < -90:
                    rotation += 180

                x, y = self._polar_to_xy(r_label, angle)
                ax.text(
                    x, y, abbrev,
                    ha="center", va="center",
                    fontsize=month_label_size, color=_label_color,
                    rotation=rotation, rotation_mode="anchor",
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
                    color=_year_color, fontweight="bold", zorder=5,
                )

        # Axis limits
        lim = (max_label_r if show_month_labels else outer_r) + 0.3
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)

        if self.title:
            fig.suptitle(self.title, fontsize=13, y=0.98, color=_year_color)

        if colourbar:
            sm = plt.cm.ScalarMappable(norm=self.norm, cmap=self.cmap)
            sm.set_array([])
            cbar = fig.colorbar(sm, ax=ax, shrink=0.5, pad=0.05, aspect=25)
            if colourbar_label:
                cbar.set_label(colourbar_label)

        fig.tight_layout()
        return fig, ax


def plot_spiral_static(
    data: pd.Series,
    *,
    cmap: Union[str, mcolors.Colormap, None] = None,
    inner_radius: float = 0.1,
    ring_width: float = 1.0,
    start_month: int = 1,
    title: Optional[str] = None,
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
    log_scale: bool = False,
    week_gap: float = 0.06,
    year_gap: float = 0.15,
    max_years: int = 9,
    cutoff: Optional[float] = None,
    cutoff_fn: Optional[Callable[[np.ndarray], float]] = None,
    figsize: tuple[float, float] = (9, 9),
    show_month_labels: bool = True,
    show_year_labels: bool = True,
    colourbar: bool = False,
    colourbar_label: Optional[str] = None,
    dark_mode: bool = False,
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
        max_years=max_years,
        cutoff=cutoff,
        cutoff_fn=cutoff_fn,
    )
    return spiral.plot(
        figsize=figsize,
        show_month_labels=show_month_labels,
        show_year_labels=show_year_labels,
        colourbar=colourbar,
        colourbar_label=colourbar_label,
        dark_mode=dark_mode,
    )
