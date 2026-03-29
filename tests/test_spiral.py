"""Tests for the matplotlib static spiral."""

import numpy as np
import pandas as pd
import pytest

matplotlib = pytest.importorskip("matplotlib", reason="matplotlib not installed")
import matplotlib.pyplot as plt
import matplotlib.figure

from seasonal_spirals import SeasonalSpiral, plot_spiral_static


class TestSeasonalSpiral:
    def test_construction(self, daily_three_years):
        s = SeasonalSpiral(daily_three_years)
        assert s.vmin < s.vmax

    def test_non_datetime_index_raises(self, non_datetime_index):
        with pytest.raises(TypeError, match="DatetimeIndex"):
            SeasonalSpiral(non_datetime_index)

    def test_invalid_start_month_raises(self, daily_one_year):
        with pytest.raises(ValueError, match="start_month"):
            SeasonalSpiral(daily_one_year, start_month=0)

    def test_vmin_vmax_respected(self, daily_three_years):
        s = SeasonalSpiral(daily_three_years, vmin=20.0, vmax=80.0)
        assert s.vmin == 20.0
        assert s.vmax == 80.0

    def test_drops_nans(self, daily_with_nans):
        s = SeasonalSpiral(daily_with_nans)
        assert s.data.isna().sum() == 0

    def test_plot_returns_fig_ax(self, daily_three_years):
        s = SeasonalSpiral(daily_three_years)
        fig, ax = s.plot()
        assert isinstance(fig, matplotlib.figure.Figure)
        assert isinstance(ax, plt.Axes)
        plt.close(fig)

    def test_log_scale(self, daily_three_years):
        import matplotlib.colors as mcolors
        s = SeasonalSpiral(daily_three_years, log_scale=True)
        assert isinstance(s.norm, mcolors.LogNorm)

    def test_custom_figsize(self, daily_one_year):
        s = SeasonalSpiral(daily_one_year)
        fig, ax = s.plot(figsize=(5, 5))
        w, h = fig.get_size_inches()
        assert w == pytest.approx(5.0)
        assert h == pytest.approx(5.0)
        plt.close(fig)

    def test_non_numeric_raises(self, non_numeric_data):
        with pytest.raises(TypeError, match="numeric"):
            SeasonalSpiral(non_numeric_data)

    def test_all_nan_raises(self, all_nan_data):
        with pytest.raises(ValueError, match="empty"):
            SeasonalSpiral(all_nan_data)

    def test_max_years_trims(self, daily_twelve_years):
        s = SeasonalSpiral(daily_twelve_years, max_years=5)
        years = sorted(set(dt.year for dt in s.data.index))
        assert len(years) == 5
        assert years[0] == 2017  # keeps most recent 5


class TestPlotSpiralStatic:
    def test_returns_fig_ax(self, daily_three_years):
        fig, ax = plot_spiral_static(daily_three_years)
        assert isinstance(fig, matplotlib.figure.Figure)
        assert isinstance(ax, plt.Axes)
        plt.close(fig)

    def test_title(self, daily_one_year):
        fig, ax = plot_spiral_static(daily_one_year, title="Test title")
        assert fig.texts[0].get_text() == "Test title"
        plt.close(fig)

    def test_single_year(self, daily_one_year):
        fig, ax = plot_spiral_static(daily_one_year)
        assert isinstance(fig, matplotlib.figure.Figure)
        plt.close(fig)

    def test_log_scale(self, daily_three_years):
        fig, ax = plot_spiral_static(daily_three_years, log_scale=True)
        assert isinstance(fig, matplotlib.figure.Figure)
        plt.close(fig)

    def test_no_month_labels(self, daily_one_year):
        fig, ax = plot_spiral_static(daily_one_year, show_month_labels=False, show_year_labels=False)
        assert isinstance(fig, matplotlib.figure.Figure)
        plt.close(fig)

    def test_cutoff_fn_parameter_exists(self):
        import inspect
        sig_static = inspect.signature(plot_spiral_static)
        sig_class = inspect.signature(SeasonalSpiral.__init__)
        assert "cutoff_fn" in sig_static.parameters
        assert "cutoff_fn" in sig_class.parameters

    def test_cutoff_fn_default_is_none(self):
        import inspect
        sig = inspect.signature(plot_spiral_static)
        assert sig.parameters["cutoff_fn"].default is None

    def test_tz_aware_index_does_not_crash(self):
        dates = pd.date_range("2022-01-01", "2022-12-31", freq="D", tz="UTC")
        rng = np.random.default_rng(42)
        data = pd.Series(rng.uniform(10, 100, len(dates)), index=dates)
        s = SeasonalSpiral(data)
        fig, ax = s.plot()
        assert isinstance(fig, matplotlib.figure.Figure)
        plt.close(fig)

    def test_start_month_october_boundary(self):
        # Data from Sep 2021 (before Oct start) through Nov 2022 (after Oct start)
        dates = pd.date_range("2021-09-01", "2022-11-30", freq="D")
        rng = np.random.default_rng(42)
        data = pd.Series(rng.uniform(10, 100, len(dates)), index=dates)

        s = SeasonalSpiral(data, start_month=10)
        # Sep 2021 (month 9 < 10) is in spiral year 2020; Oct 2021+ is in 2021, etc.
        # Verify no error and produces a valid figure
        fig, ax = s.plot()
        assert isinstance(fig, matplotlib.figure.Figure)
        plt.close(fig)
