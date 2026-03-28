"""Tests for the Plotly interactive spiral."""

import numpy as np
import pandas as pd
import pytest
import plotly.graph_objects as go

from seasonal_spirals import plot_spiral


class TestPlotSpiralInteractive:
    def test_returns_figure(self, daily_three_years):
        fig = plot_spiral(daily_three_years)
        assert isinstance(fig, go.Figure)

    def test_single_year(self, daily_one_year):
        fig = plot_spiral(daily_one_year)
        assert isinstance(fig, go.Figure)

    def test_has_barpolar_trace(self, daily_three_years):
        fig = plot_spiral(daily_three_years)
        bar_traces = [t for t in fig.data if isinstance(t, go.Barpolar)]
        assert len(bar_traces) == 1

    def test_barpolar_length_matches_data(self, daily_three_years):
        data = daily_three_years.dropna()
        fig = plot_spiral(data)
        trace = next(t for t in fig.data if isinstance(t, go.Barpolar))
        assert len(trace.r) == len(data)

    def test_title_set(self, daily_one_year):
        fig = plot_spiral(daily_one_year, title="My title")
        assert fig.layout.title.text == "My title"

    def test_dimensions(self, daily_one_year):
        fig = plot_spiral(daily_one_year, height=500, width=600)
        assert fig.layout.height == 500
        assert fig.layout.width == 600

    def test_drops_nans(self, daily_with_nans):
        n_valid = daily_with_nans.dropna().shape[0]
        fig = plot_spiral(daily_with_nans)
        trace = next(t for t in fig.data if isinstance(t, go.Barpolar))
        assert len(trace.r) == n_valid

    def test_log_scale(self, daily_three_years):
        fig = plot_spiral(daily_three_years, log_scale=True)
        assert isinstance(fig, go.Figure)

    def test_custom_vmin_vmax(self, daily_three_years):
        fig = plot_spiral(daily_three_years, vmin=20.0, vmax=80.0)
        assert isinstance(fig, go.Figure)

    def test_non_datetime_index_raises(self, non_datetime_index):
        with pytest.raises(TypeError, match="DatetimeIndex"):
            plot_spiral(non_datetime_index)

    def test_invalid_start_month_raises(self, daily_one_year):
        with pytest.raises(ValueError, match="start_month"):
            plot_spiral(daily_one_year, start_month=13)

    def test_start_month_zero_raises(self, daily_one_year):
        with pytest.raises(ValueError, match="start_month"):
            plot_spiral(daily_one_year, start_month=0)

    def test_start_month_valid(self, daily_three_years):
        fig = plot_spiral(daily_three_years, start_month=4)
        assert isinstance(fig, go.Figure)

    def test_has_year_labels(self, daily_three_years):
        fig = plot_spiral(daily_three_years)
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatterpolar)]
        assert len(scatter_traces) == 1
        assert len(scatter_traces[0].text) == 3  # 2020, 2021, 2022

    def test_has_month_annotations(self, daily_three_years):
        fig = plot_spiral(daily_three_years)
        assert len(fig.layout.annotations) == 12

    def test_non_numeric_raises(self, non_numeric_data):
        with pytest.raises(TypeError, match="numeric"):
            plot_spiral(non_numeric_data)

    def test_all_nan_raises(self, all_nan_data):
        with pytest.raises(ValueError, match="empty"):
            plot_spiral(all_nan_data)

    def test_max_years_trims_data(self, daily_twelve_years):
        fig = plot_spiral(daily_twelve_years, max_years=5)
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatterpolar)]
        assert len(scatter_traces[0].text) == 5
