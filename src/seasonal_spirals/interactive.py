"""
Interactive seasonal spiral using Plotly.

Provides the same Archimedean spiral layout as the matplotlib version
but with hover tooltips showing date, value, and day of week.
"""

from __future__ import annotations

import calendar
from typing import Optional, Union

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from seasonal_spirals._colormap import (
    WIKISPIRAL_PLOTLY,
    HybridNorm,
    auto_cutoff,
)

MONTH_ABBREVS = list(calendar.month_abbr[1:])
DAY_NAMES = list(calendar.day_name)  # Monday … Sunday
N_WEEKS = 52


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
    cutoff_n: float = 3.0,
    cutoff_percentile: float = 75.0,
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

    # Keep only the most recent max_years of data
    if max_years is not None and max_years > 0:
        all_years = sorted(set(
            dt.year if start_month == 1 or dt.month >= start_month
            else dt.year - 1
            for dt in data.index
        ))
        if len(all_years) > max_years:
            keep_years = set(all_years[-max_years:])
            data = data[
                data.index.map(
                    lambda dt: (dt.year if start_month == 1 or dt.month >= start_month
                                else dt.year - 1) in keep_years
                )
            ]

    vals = data.values.astype(float)
    vmin_ = float(vmin) if vmin is not None else float(np.nanmin(vals))
    vmax_ = float(vmax) if vmax is not None else float(np.nanmax(vals))

    # Choose colour scheme:
    # - wikispiral hybrid (default): linear-log with auto cutoff
    # - log_scale=True: pure log, user-supplied or YLGNBU colorscale
    # - colorscale supplied: user controls everything
    _use_wikispiral = (colorscale is None and not log_scale)
    if _use_wikispiral:
        _cutoff = cutoff if cutoff is not None else auto_cutoff(
            vals, vmin_, vmax_, cutoff_n, cutoff_percentile
        )
        _hybrid_norm = HybridNorm(vmin_, vmax_, _cutoff)
        _colorscale = WIKISPIRAL_PLOTLY
    else:
        _hybrid_norm = None
        _colorscale = colorscale if colorscale is not None else "YlGnBu"

    # Spiral constants
    week_increment = (ring_width + year_gap) / N_WEEKS
    day_band = ring_width / 7.0
    slot_deg = 360.0 / N_WEEKS
    arc_width_deg = slot_deg * (1.0 - week_gap)

    # Determine spiral years
    def spiral_year(dt: pd.Timestamp) -> int:
        if start_month == 1 or dt.month >= start_month:
            return dt.year
        return dt.year - 1

    def year_start(sy: int) -> pd.Timestamp:
        return pd.Timestamp(year=sy, month=start_month, day=1)

    spiral_years = sorted(set(spiral_year(dt) for dt in data.index))
    min_year = spiral_years[0]

    # Build arrays for go.Barpolar
    r_vals = []       # bar height (radial extent)
    base_vals = []    # inner radius
    theta_vals = []   # centre angle in degrees
    width_vals = []   # angular width in degrees
    colour_vals = []  # raw value for colour mapping
    hover_texts = []  # custom hover text

    for dt, value in data.items():
        sy = spiral_year(dt)
        ys = year_start(sy)
        year_idx = sy - min_year
        day_offset = (dt.normalize() - ys).days
        weekday = dt.weekday()  # 0=Mon … 6=Sun

        week_num = min(day_offset // 7, N_WEEKS - 1)

        # Angular: centre of the week slot (degrees, clockwise from North)
        theta_centre = week_num * slot_deg + arc_width_deg / 2.0

        # Radial: continuous spiral
        total_weeks = year_idx * N_WEEKS + week_num
        base_r = inner_radius + total_weeks * week_increment
        r_inner = base_r + weekday * day_band
        r_outer = r_inner + day_band

        r_vals.append(r_outer - r_inner)
        base_vals.append(r_inner)
        theta_vals.append(theta_centre)
        width_vals.append(arc_width_deg)

        fval = float(value)
        if _use_wikispiral:
            colour_vals.append(fval)  # raw; normalised below after loop
        elif log_scale:
            colour_vals.append(np.log10(max(fval, 1e-10)))
        else:
            colour_vals.append(fval)

        hover_texts.append(
            f"<b>{dt.strftime('%a %d %b %Y')}</b><br>"
            f"Value: {fval:,.0f}"
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
            colorscale=_colorscale,
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

    # Per-angle month label positions (matching matplotlib layout)
    last_dt = data.index[-1]
    last_sy = spiral_year(last_dt)
    last_ys = year_start(last_sy)
    last_day_offset = (last_dt.normalize() - last_ys).days
    last_week = min(last_day_offset // 7, N_WEEKS - 1)
    last_year_idx = last_sy - min_year

    month_label_rs = []
    month_label_angles = []
    month_label_texts = []
    for m in range(12):
        angle_deg = m * 30.0
        week_at_angle = int(angle_deg / slot_deg)

        if week_at_angle <= last_week:
            outermost_total = last_year_idx * N_WEEKS + week_at_angle
        else:
            outermost_total = (last_year_idx - 1) * N_WEEKS + week_at_angle

        r_label = inner_radius + outermost_total * week_increment + ring_width + 0.25

        month_label_rs.append(r_label)
        month_label_angles.append(angle_deg)
        month_label_texts.append(MONTH_ABBREVS[(start_month - 1 + m) % 12].upper())

    r_max = max(month_label_rs) + 0.3

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
            bgcolor="white",
        ),
        # Hidden Cartesian axes overlaid on the polar area for label positioning.
        # This avoids the fragile paper-coordinate conversion.
        xaxis=dict(range=[-r_max, r_max], visible=False),
        yaxis=dict(range=[-r_max, r_max], visible=False, scaleanchor="x"),
        showlegend=False,
        title=dict(text=title or "", font=dict(size=14)),
        height=height,
        width=width,
        margin=dict(l=60, r=60, t=60, b=60),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )

    # Month labels as annotations in Cartesian coords (tangentially rotated)
    for i in range(12):
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
            font=dict(size=10, color="#444"),
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
        textfont=dict(size=8, color="#999"),
        textposition="middle right",
        hoverinfo="skip",
        showlegend=False,
    ))

    return fig
