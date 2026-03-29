"""Unit tests for the WikiSpiral hybrid colour scheme."""

import numpy as np
import pytest

from seasonal_spirals._colormap import (
    WIKISPIRAL_PLOTLY,
    HybridNorm,
    auto_cutoff,
)


class TestAutoCutoff:
    def test_empty_array_returns_midpoint(self):
        result = auto_cutoff([], vmin=0.0, vmax=100.0)
        assert result == pytest.approx(50.0)

    def test_all_nan_returns_midpoint(self):
        result = auto_cutoff([float("nan"), float("nan")], vmin=0.0, vmax=100.0)
        assert result == pytest.approx(50.0)

    def test_basic_heuristic(self):
        vals = list(range(1, 101))  # 1..100, 75th percentile = 75.75
        result = auto_cutoff(vals, vmin=0.0, vmax=200.0, cutoff_n=2.0, cutoff_percentile=75.0)
        assert result > 0.0
        assert result < 200.0

    def test_clamps_below_vmin_plus_eps(self):
        # cutoff_n * p75 would be extremely small (near 0); should clamp up
        vals = [0.0001] * 100
        result = auto_cutoff(vals, vmin=0.0, vmax=100.0, cutoff_n=1.0, cutoff_percentile=50.0)
        eps = (100.0 - 0.0) * 0.05
        assert result >= 0.0 + eps - 1e-10

    def test_clamps_above_vmax_minus_eps(self):
        # cutoff_n * p75 would be huge; should clamp down
        vals = [1e9] * 100
        result = auto_cutoff(vals, vmin=0.0, vmax=100.0, cutoff_n=10.0, cutoff_percentile=99.0)
        eps = (100.0 - 0.0) * 0.05
        assert result <= 100.0 - eps + 1e-10

    def test_result_within_bounds(self):
        vals = list(range(100))
        result = auto_cutoff(vals, vmin=0.0, vmax=200.0)
        assert 0.0 < result < 200.0


class TestHybridNorm:
    def _norm(self, vmin=0.0, vmax=100.0, cutoff=50.0):
        return HybridNorm(vmin=vmin, vmax=vmax, cutoff=cutoff)

    def test_value_at_cutoff_maps_to_half(self):
        norm = self._norm()
        result = norm(np.array([50.0]))
        assert result[0] == pytest.approx(0.5)

    def test_vmin_maps_to_zero(self):
        norm = self._norm()
        result = norm(np.array([0.0]))
        assert result[0] == pytest.approx(0.0)

    def test_vmax_maps_to_one(self):
        norm = self._norm()
        result = norm(np.array([100.0]))
        assert result[0] == pytest.approx(1.0)

    def test_value_below_vmin_clips_to_zero(self):
        norm = self._norm()
        result = norm(np.array([-10.0]))
        assert result[0] == pytest.approx(0.0)

    def test_value_above_vmax_clips_to_one(self):
        norm = self._norm()
        result = norm(np.array([200.0]))
        assert result[0] == pytest.approx(1.0)

    def test_linear_segment_monotone(self):
        norm = self._norm()
        vals = np.linspace(0.0, 50.0, 20)
        results = norm(vals)
        assert np.all(np.diff(results) >= 0)

    def test_log_segment_monotone(self):
        norm = self._norm()
        vals = np.linspace(50.0, 100.0, 20)
        results = norm(vals)
        assert np.all(np.diff(results) >= 0)

    def test_log_range_zero_maps_log_mask_to_one(self):
        # cutoff == vmax means log_range == 0
        norm = HybridNorm(vmin=0.0, vmax=100.0, cutoff=100.0)
        # Values above cutoff get result = 1.0
        result = norm(np.array([110.0]))
        assert result[0] == pytest.approx(1.0)

    def test_output_always_in_zero_one(self):
        norm = self._norm()
        vals = np.linspace(-50.0, 200.0, 100)
        results = norm(vals)
        assert np.all(results >= 0.0)
        assert np.all(results <= 1.0)

    def test_midpoint_is_at_cutoff(self):
        # A value just below cutoff should be just under 0.5;
        # a value just above should be just over 0.5
        norm = self._norm(cutoff=40.0)
        below = norm(np.array([39.999]))[0]
        above = norm(np.array([40.001]))[0]
        assert below < 0.5
        assert above > 0.5


class TestWikispiralPlotly:
    def test_ten_stops(self):
        assert len(WIKISPIRAL_PLOTLY) == 10

    def test_positions_in_zero_one(self):
        for pos, _ in WIKISPIRAL_PLOTLY:
            assert 0.0 <= pos <= 1.0

    def test_first_position_is_zero(self):
        assert WIKISPIRAL_PLOTLY[0][0] == pytest.approx(0.0)

    def test_last_position_is_one(self):
        assert WIKISPIRAL_PLOTLY[-1][0] == pytest.approx(1.0)

    def test_positions_non_decreasing(self):
        positions = [p for p, _ in WIKISPIRAL_PLOTLY]
        assert all(a <= b for a, b in zip(positions, positions[1:]))

    def test_colors_are_rgb_strings(self):
        for _, color in WIKISPIRAL_PLOTLY:
            assert color.startswith("rgb(")
