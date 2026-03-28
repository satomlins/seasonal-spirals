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
