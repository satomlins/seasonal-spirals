"""Unit tests for shared spiral geometry utilities."""

import numpy as np
import pandas as pd
import pytest

from seasonal_spirals._geometry import (
    N_WEEKS,
    spiral_year,
    spiral_year_start,
    trim_to_max_years,
    tile_geometry,
    month_label_positions,
)


class TestSpiralYear:
    def test_january_start_same_year(self):
        assert spiral_year(pd.Timestamp("2022-06-15"), start_month=1) == 2022

    def test_january_start_jan_1(self):
        assert spiral_year(pd.Timestamp("2022-01-01"), start_month=1) == 2022

    def test_october_start_before_start_month(self):
        # Sep is before Oct start, so belongs to the previous spiral year
        assert spiral_year(pd.Timestamp("2022-09-15"), start_month=10) == 2021

    def test_october_start_on_start_month(self):
        assert spiral_year(pd.Timestamp("2022-10-01"), start_month=10) == 2022

    def test_october_start_after_start_month(self):
        assert spiral_year(pd.Timestamp("2022-11-30"), start_month=10) == 2022

    def test_october_start_in_next_calendar_year(self):
        # Jan 2023 is still inside spiral year 2022 (Oct 2022 - Sep 2023)
        assert spiral_year(pd.Timestamp("2023-01-15"), start_month=10) == 2022

    def test_july_start_on_boundary(self):
        assert spiral_year(pd.Timestamp("2022-07-01"), start_month=7) == 2022

    def test_july_start_before_boundary(self):
        assert spiral_year(pd.Timestamp("2022-06-30"), start_month=7) == 2021


class TestSpiralYearStart:
    def test_january_start(self):
        ts = spiral_year_start(2022, start_month=1)
        assert ts == pd.Timestamp("2022-01-01")

    def test_october_start(self):
        ts = spiral_year_start(2021, start_month=10)
        assert ts == pd.Timestamp("2021-10-01")

    def test_july_start(self):
        ts = spiral_year_start(2020, start_month=7)
        assert ts == pd.Timestamp("2020-07-01")


class TestTrimToMaxYears:
    def _make_data(self, start, end):
        dates = pd.date_range(start, end, freq="D")
        rng = np.random.default_rng(0)
        return pd.Series(rng.uniform(1, 10, len(dates)), index=dates)

    def test_none_returns_unchanged(self):
        data = self._make_data("2020-01-01", "2022-12-31")
        result = trim_to_max_years(data, start_month=1, max_years=None)
        assert len(result) == len(data)

    def test_zero_returns_unchanged(self):
        data = self._make_data("2020-01-01", "2022-12-31")
        result = trim_to_max_years(data, start_month=1, max_years=0)
        assert len(result) == len(data)

    def test_keeps_most_recent_years(self):
        data = self._make_data("2018-01-01", "2022-12-31")
        result = trim_to_max_years(data, start_month=1, max_years=3)
        years = sorted(set(dt.year for dt in result.index))
        assert years == [2020, 2021, 2022]

    def test_fewer_years_than_max_unchanged(self):
        data = self._make_data("2021-01-01", "2022-12-31")
        result = trim_to_max_years(data, start_month=1, max_years=5)
        assert len(result) == len(data)

    def test_non_january_start(self):
        # Data Oct 2019 - Nov 2022 with start_month=10:
        #   spiral years: 2019, 2020, 2021, 2022
        data = self._make_data("2019-10-01", "2022-11-30")
        result = trim_to_max_years(data, start_month=10, max_years=2)
        sy = sorted(set(spiral_year(dt, 10) for dt in result.index))
        assert sy == [2021, 2022]


class TestTileGeometry:
    def _geom(self, day_offset=0, year_idx=0, weekday=0):
        return tile_geometry(
            day_offset, year_idx, weekday,
            inner_radius=0.1, ring_width=1.0, week_gap=0.06, year_gap=0.15,
        )

    def test_r_inner_less_than_r_outer(self):
        for weekday in range(7):
            _, _, r_inner, r_outer = self._geom(weekday=weekday)
            assert r_inner < r_outer

    def test_monday_innermost_sunday_outermost(self):
        _, _, r_inner_mon, _ = self._geom(weekday=0)
        _, _, _, r_outer_sun = self._geom(weekday=6)
        assert r_inner_mon < r_outer_sun

    def test_weekday_bands_adjacent(self):
        # r_outer of weekday N should equal r_inner of weekday N+1
        for wd in range(6):
            _, _, _, r_outer = self._geom(weekday=wd)
            _, _, r_inner_next, _ = self._geom(weekday=wd + 1)
            assert r_outer == pytest.approx(r_inner_next)

    def test_arc_width_less_than_slot(self):
        arc_start, arc_width, _, _ = self._geom()
        slot_rad = 2.0 * np.pi / N_WEEKS
        assert arc_width < slot_rad

    def test_day_offset_clamped_to_last_week(self):
        # day_offset beyond 52 weeks should clamp to week 51
        _, _, _, _ = tile_geometry(
            400, 0, 0, inner_radius=0.1, ring_width=1.0, week_gap=0.06, year_gap=0.15
        )
        # No error means clamping works; verify clamped week
        arc_start_clamped, _, _, _ = tile_geometry(
            51 * 7, 0, 0, inner_radius=0.1, ring_width=1.0, week_gap=0.06, year_gap=0.15
        )
        arc_start_beyond, _, _, _ = tile_geometry(
            400, 0, 0, inner_radius=0.1, ring_width=1.0, week_gap=0.06, year_gap=0.15
        )
        assert arc_start_clamped == pytest.approx(arc_start_beyond)

    def test_adjacent_weeks_non_overlapping(self):
        # arc_start + arc_width of week N must not exceed arc_start of week N+1
        slot_rad = 2.0 * np.pi / N_WEEKS
        arc_start_0, arc_width_0, _, _ = self._geom(day_offset=0)
        arc_start_1, _, _, _ = self._geom(day_offset=7)
        assert arc_start_0 + arc_width_0 <= arc_start_1 + 1e-10

    def test_year_idx_increases_radius(self):
        _, _, r_inner_y0, _ = self._geom(year_idx=0)
        _, _, r_inner_y1, _ = self._geom(year_idx=1)
        assert r_inner_y1 > r_inner_y0


class TestMonthLabelPositions:
    def test_returns_twelve_labels_for_full_year(self):
        sy = 2022
        year_start_ts = spiral_year_start(sy, start_month=1)
        results = month_label_positions(
            sy, year_start_ts, start_month=1,
            inner_radius=0.1, ring_width=1.0, year_gap=0.15,
            last_year_idx=0, last_week=51,
        )
        assert len(results) == 12

    def test_each_tuple_has_four_elements(self):
        sy = 2022
        year_start_ts = spiral_year_start(sy, start_month=1)
        for item in month_label_positions(
            sy, year_start_ts, start_month=1,
            inner_radius=0.1, ring_width=1.0, year_gap=0.15,
            last_year_idx=0, last_week=51,
        ):
            assert len(item) == 4

    def test_angles_in_range(self):
        sy = 2022
        year_start_ts = spiral_year_start(sy, start_month=1)
        for angle, _, _, _ in month_label_positions(
            sy, year_start_ts, start_month=1,
            inner_radius=0.1, ring_width=1.0, year_gap=0.15,
            last_year_idx=0, last_week=51,
        ):
            assert 0.0 <= angle <= 2.0 * np.pi + 1e-10

    def test_r_label_positive(self):
        sy = 2022
        year_start_ts = spiral_year_start(sy, start_month=1)
        for _, _, _, r_label in month_label_positions(
            sy, year_start_ts, start_month=1,
            inner_radius=0.1, ring_width=1.0, year_gap=0.15,
            last_year_idx=0, last_week=51,
        ):
            assert r_label > 0.0

    def test_october_start_first_label_is_oct(self):
        sy = 2021
        year_start_ts = spiral_year_start(sy, start_month=10)
        results = month_label_positions(
            sy, year_start_ts, start_month=10,
            inner_radius=0.1, ring_width=1.0, year_gap=0.15,
            last_year_idx=0, last_week=51,
        )
        first_abbrev = results[0][1]
        assert first_abbrev == "OCT"
