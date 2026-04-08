"""
Interactive seasonal spiral using Plotly.

Provides the same Archimedean spiral layout as the matplotlib version
but with hover tooltips showing date, value, and day of week.
"""

from __future__ import annotations

from typing import Callable, Optional, Union

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from seasonal_spirals._colourmap import (
    WIKISPIRAL_PLOTLY,
    HybridNorm,
    auto_cutoff,
)
from seasonal_spirals._geometry import (
    N_WEEKS,
    spiral_year,
    spiral_year_start,
    trim_to_max_years,
    tile_geometry,
    month_label_positions,
)

def plot_spiral(
    data: pd.Series,
    *,
    colorscale: Union[str, list, None] = None,
    inner_radius: float = 0.1,
    ring_width: float = 1.0,
    start_month: int = 1,
    title: Optional[str] = None,
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
    log_scale: bool = False,
    week_gap: float = 0.06,
    year_gap: float = 0.15,
    height: int = 700,
    width: int = 700,
    colourbar_label: Optional[str] = None,
    max_years: int = 9,
    cutoff: Optional[float] = None,
    cutoff_fn: Optional[Callable[[np.ndarray], float]] = None,
    dark_mode: bool = False,
) -> go.Figure:
    """Create an interactive seasonal spiral chart with hover tooltips."""
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

    data = data.dropna().sort_index()
    if len(data) == 0:
        raise ValueError("data is empty (or all NaN)")

    # Strip timezone info if present — daily data, tz not relevant for date math
    if getattr(data.index, "tz", None) is not None:
        data = data.copy()
        data.index = data.index.tz_localize(None)

    data = trim_to_max_years(data, start_month, max_years)

    vals = data.values.astype(float)
    vmin_ = float(vmin) if vmin is not None else float(np.nanmin(vals))
    vmax_ = float(vmax) if vmax is not None else float(np.nanmax(vals))

    # Choose colour scheme:
    # - wikispiral hybrid (default): linear-log with auto cutoff
    # - log_scale=True: pure log, user-supplied or YlGnBu colourscale
    # - colourscale supplied: user controls everything
    _use_wikispiral = (colorscale is None and not log_scale)
    if _use_wikispiral:
        if cutoff is not None:
            _cutoff = float(cutoff)
        elif cutoff_fn is not None:
            _raw = float(cutoff_fn(vals))
            _eps = (vmax_ - vmin_) * 0.05
            _cutoff = float(np.clip(_raw, vmin_ + _eps, vmax_ - _eps))
        else:
            _cutoff = auto_cutoff(vals, vmin_, vmax_)
        _hybrid_norm = HybridNorm(vmin_, vmax_, _cutoff)
        _colourscale = WIKISPIRAL_PLOTLY
    else:
        _hybrid_norm = None
        _colourscale = colorscale if colorscale is not None else "YlGnBu"

    # Spiral constants (used for outer_r and year label positions)
    week_increment = (ring_width + year_gap) / N_WEEKS
    day_band = ring_width / 7.0

    # Hover value format: use integers if all data are whole numbers, else 3 sig figs
    _is_int_data = bool(np.all(vals == np.floor(vals)))
    _val_fmt = ",.0f" if _is_int_data else ",.3g"

    # Determine spiral years
    spiral_years = sorted(set(spiral_year(dt, start_month) for dt in data.index))
    min_year = spiral_years[0]

    # Build arrays for go.Barpolar
    r_vals = []       # bar height (radial extent)
    base_vals = []    # inner radius
    theta_vals = []   # centre angle in degrees
    width_vals = []   # angular width in degrees
    colour_vals = []  # raw value for colour mapping
    hover_texts = []  # custom hover text

    for dt, value in data.items():
        sy = spiral_year(dt, start_month)
        ys = spiral_year_start(sy, start_month)
        year_idx = sy - min_year
        day_offset = (dt.normalize() - ys).days
        weekday = dt.weekday()  # 0=Mon … 6=Sun

        arc_start_rad, arc_width_rad, r_inner, r_outer = tile_geometry(
            day_offset, year_idx, weekday,
            inner_radius, ring_width, week_gap, year_gap,
            year_start_weekday=ys.weekday(),
        )
        theta_centre = np.degrees(arc_start_rad) + np.degrees(arc_width_rad) / 2.0

        r_vals.append(r_outer - r_inner)
        base_vals.append(r_inner)
        theta_vals.append(theta_centre)
        width_vals.append(np.degrees(arc_width_rad))

        fval = float(value)
        if _use_wikispiral:
            colour_vals.append(fval)  # raw; normalised below after loop
        elif log_scale:
            colour_vals.append(np.log10(max(fval, 1e-10)))
        else:
            colour_vals.append(fval)

        hover_texts.append(
            f"<b>{dt.strftime('%a %d %b %Y')}</b><br>"
            f"Value: {fval:{_val_fmt}}"
        )

    # Normalise colour values
    if _use_wikispiral:
        colour_vals = list(_hybrid_norm(np.array(colour_vals, dtype=float)))
        cmin, cmax = 0.0, 1.0
    elif log_scale:
        cmin = np.log10(max(vmin_, 1e-10))
        cmax = np.log10(max(vmax_, 1e-10))
    else:
        cmin, cmax = vmin_, vmax_

    fig = go.Figure()

    fig.add_trace(go.Barpolar(
        r=r_vals,
        base=base_vals,
        theta=theta_vals,
        width=width_vals,
        marker=dict(
            color=colour_vals,
            colorscale=_colourscale,
            cmin=cmin,
            cmax=cmax,
            showscale=False,
            line=dict(width=0),
        ),
        hovertext=hover_texts,
        hoverinfo="text",
    ))

    n_years = len(spiral_years)
    outer_r = inner_radius + n_years * N_WEEKS * week_increment + 6 * day_band

    # Per-angle month label positions (calendar-accurate, matching matplotlib)
    last_dt = data.index[-1]
    last_sy = spiral_year(last_dt, start_month)
    last_ys = spiral_year_start(last_sy, start_month)
    last_day_offset = (last_dt.normalize() - last_ys).days
    last_year_idx = last_sy - min_year

    label_tuples = month_label_positions(
        last_sy, last_ys, start_month,
        inner_radius, ring_width, year_gap,
        last_year_idx, last_day_offset,
        year_start_weekday=last_ys.weekday(),
    )

    month_label_rs = [r for _, _, _, r in label_tuples]
    month_label_angles = [np.degrees(angle) for angle, _, _, _ in label_tuples]
    month_label_texts = [abbrev for _, abbrev, _, _ in label_tuples]

    r_max = max(month_label_rs) + 0.3

    _bg = "#0f1117" if dark_mode else "white"
    _label_color = "#e6edf3" if dark_mode else "#444"
    _year_color = "#e6edf3" if dark_mode else "#999"

    fig.update_layout(
        polar=dict(
            angularaxis=dict(
                direction="clockwise",
                rotation=90,
                showticklabels=False,
                showgrid=False,
                showline=False,
            ),
            radialaxis=dict(
                visible=False,
                range=[0, r_max],
            ),
            bgcolor=_bg,
        ),
        # Hidden Cartesian axes overlaid on the polar area for label positioning.
        # This avoids the fragile paper-coordinate conversion.
        xaxis=dict(range=[-r_max, r_max], visible=False),
        yaxis=dict(range=[-r_max, r_max], visible=False, scaleanchor="x"),
        showlegend=False,
        title=dict(text=title or "", font=dict(size=14, color=_label_color)),
        height=height,
        width=width,
        margin=dict(l=60, r=60, t=60, b=60),
        paper_bgcolor=_bg,
        plot_bgcolor=_bg,
    )

    # Month labels as annotations in Cartesian coords (tangentially rotated)
    for i in range(len(label_tuples)):
        angle_rad = np.radians(month_label_angles[i])
        x_cart = month_label_rs[i] * np.sin(angle_rad)
        y_cart = month_label_rs[i] * np.cos(angle_rad)

        # Tangential: perpendicular to radial, flipped for readability.
        # Plotly textangle is CW-positive (opposite of matplotlib rotation).
        textangle = month_label_angles[i] % 360
        if textangle > 180:
            textangle -= 360
        if textangle > 90:
            textangle -= 180
        elif textangle < -90:
            textangle += 180

        fig.add_annotation(
            text=month_label_texts[i],
            x=x_cart, y=y_cart,
            xref="x", yref="y",
            showarrow=False,
            font=dict(size=10, color=_label_color),
            textangle=textangle,
        )

    # Year labels - bold grey, positioned just right of Jan
    label_angle = 4.0
    label_rs = []
    label_texts = []
    for i, sy in enumerate(spiral_years):
        r_c = (inner_radius
               + (i * N_WEEKS + N_WEEKS // 2) * week_increment
               + 3 * day_band)
        label_rs.append(r_c)
        label_texts.append(f"<b>{sy}</b>")

    fig.add_trace(go.Scatterpolar(
        r=label_rs,
        theta=[label_angle] * len(label_rs),
        mode="text",
        text=label_texts,
        textfont=dict(size=8, color=_year_color),
        textposition="middle right",
        hoverinfo="skip",
        showlegend=False,
    ))

    return fig
