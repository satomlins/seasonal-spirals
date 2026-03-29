"""
Shared spiral geometry utilities.

Both the Plotly (interactive.py) and Matplotlib (spiral.py) backends
use identical coordinate math. This module is the single source of truth.

Coordinate convention
---------------------
Angles are in radians, increasing clockwise from North (12 o'clock = 0).
Radial values increase outward from the centre.
"""
from __future__ import annotations

import calendar
from typing import Optional

import numpy as np
import pandas as pd

N_WEEKS: int = 52
MONTH_ABBREVS: list[str] = list(calendar.month_abbr[1:])


def spiral_year(dt: pd.Timestamp, start_month: int) -> int:
    """Return the spiral year for a date, accounting for non-January starts.

    A spiral year begins on the first day of *start_month*.  Dates that fall
    before *start_month* in a calendar year belong to the preceding spiral year.

    Parameters
    ----------
    dt:
        The date to classify.
    start_month:
        Month number (1-12) at which each spiral year begins.

    Examples
    --------
    >>> spiral_year(pd.Timestamp("2022-09-15"), start_month=10)
    2021
    >>> spiral_year(pd.Timestamp("2022-10-01"), start_month=10)
    2022
    >>> spiral_year(pd.Timestamp("2022-06-01"), start_month=1)
    2022
    """
    if start_month == 1 or dt.month >= start_month:
        return dt.year
    return dt.year - 1


def spiral_year_start(sy: int, start_month: int) -> pd.Timestamp:
    """Return the first date of a spiral year.

    Parameters
    ----------
    sy:
        The spiral year number.
    start_month:
        Month number (1-12) at which the year begins.
    """
    return pd.Timestamp(year=sy, month=start_month, day=1)


def trim_to_max_years(
    data: pd.Series,
    start_month: int,
    max_years: Optional[int],
) -> pd.Series:
    """Return *data* trimmed to the most recent *max_years* spiral years.

    If the data spans fewer than *max_years* years, it is returned unchanged.
    """
    if max_years is None or max_years <= 0:
        return data
    all_years = sorted(set(spiral_year(dt, start_month) for dt in data.index))
    if len(all_years) <= max_years:
        return data
    keep = set(all_years[-max_years:])
    return data[data.index.map(lambda dt: spiral_year(dt, start_month) in keep)]


def tile_geometry(
    day_offset: int,
    year_idx: int,
    weekday: int,
    inner_radius: float,
    ring_width: float,
    week_gap: float,
    year_gap: float,
) -> tuple[float, float, float, float]:
    """Compute the geometry for a single day tile on the spiral.

    Parameters
    ----------
    day_offset:
        Days elapsed since the start of the tile's spiral year.
    year_idx:
        Zero-based index of this spiral year (0 = oldest visible year).
    weekday:
        Day of week, 0 = Monday (innermost band) to 6 = Sunday (outermost).
    inner_radius:
        Radius of the central hole.
    ring_width:
        Radial width of one full spiral revolution (one year).
    week_gap:
        Fraction of each weekly angular slot left as a gap between segments.
    year_gap:
        Extra radial space inserted between year boundaries.

    Returns
    -------
    (arc_start_rad, arc_width_rad, r_inner, r_outer)
        *arc_start_rad* and *arc_width_rad* are in radians, clockwise from
        North.  *r_inner* and *r_outer* are the inner and outer radii of the
        tile's day-of-week band.
    """
    _week_increment = (ring_width + year_gap) / N_WEEKS
    _day_band = ring_width / 7.0

    week_num = min(day_offset // 7, N_WEEKS - 1)
    slot_rad = 2.0 * np.pi / N_WEEKS
    arc_width = slot_rad * (1.0 - week_gap)
    arc_start = week_num * slot_rad

    total_weeks = year_idx * N_WEEKS + week_num
    base_r = inner_radius + total_weeks * _week_increment
    r_inner = base_r + weekday * _day_band
    r_outer = r_inner + _day_band

    return float(arc_start), float(arc_width), float(r_inner), float(r_outer)


def month_label_positions(
    sy: int,
    year_start_ts: pd.Timestamp,
    start_month: int,
    inner_radius: float,
    ring_width: float,
    year_gap: float,
    last_year_idx: int,
    last_week: int,
) -> list[tuple[float, str, int, float]]:
    """Compute label positions for each month in a spiral year.

    Uses actual first-of-month calendar dates so that label angles are
    accurate regardless of *start_month* and irregularities in month length.

    Parameters
    ----------
    sy:
        The spiral year being labelled.
    year_start_ts:
        First date of this spiral year.
    start_month:
        Month number (1-12) at which each spiral year begins.
    inner_radius, ring_width, year_gap:
        Spiral geometry parameters (same as :func:`tile_geometry`).
    last_year_idx:
        Zero-based index of the last (most recent) spiral year visible.
    last_week:
        Week number (0-51) of the last data point in the most recent year.

    Returns
    -------
    list of (angle_rad, abbrev, week_num, r_label)
        *angle_rad* is clockwise from North.  *abbrev* is the uppercase
        3-letter month name.  *week_num* is the week slot (0-51).
        *r_label* is the radial distance at which to place the label.
    """
    _week_increment = (ring_width + year_gap) / N_WEEKS
    results: list[tuple[float, str, int, float]] = []

    for m in range(12):
        month_num = (start_month - 1 + m) % 12 + 1
        cal_year = sy if month_num >= start_month else sy + 1
        ts = pd.Timestamp(year=cal_year, month=month_num, day=1)
        if ts >= year_start_ts + pd.DateOffset(years=1):
            continue

        day_off = (ts - year_start_ts).days
        week_num = min(day_off // 7, N_WEEKS - 1)
        angle = week_num * (2.0 * np.pi / N_WEEKS)

        if week_num <= last_week:
            outermost_total = last_year_idx * N_WEEKS + week_num
        else:
            outermost_total = (last_year_idx - 1) * N_WEEKS + week_num
        r_label = inner_radius + outermost_total * _week_increment + ring_width + 0.25

        results.append((angle, MONTH_ABBREVS[month_num - 1].upper(), week_num, r_label))

    return results
