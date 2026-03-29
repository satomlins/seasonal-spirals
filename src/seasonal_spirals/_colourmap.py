"""
WikiSpiral hybrid linear-log colour scheme.

Design (from observablehq.com/@yurivish/seasonal-spirals):
- Linear segment: light green to dark navy (ordinary days, vmin to cutoff)
- Log segment: deep blue to coral-red via magenta (extraordinary days, cutoff to vmax)
- Cutoff threshold: Tukey IQR fence (Q3 + 1.5 * IQR) by default
- Both segments get equal visual weight (half the colourbar each)

Colours sampled directly from the WikiPulse legend for the Christmas page.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt


# Colours sampled from the WikiPulse legend (Christmas page):
# Linear segment bottom-to-top (low values to cutoff): light green -> dark navy
# Log segment bottom-to-top (cutoff to high values): deep blue -> coral red
_LINEAR_STOPS = [
    "#f3faec",  # vmin  - near-white light green
    "#bee1bf",  # 0.25
    "#7dbec8",  # 0.50  - sky blue
    "#3f7eb4",  # 0.75  - steel blue
    "#193a7f",  # cutoff - dark navy
]
_LOG_STOPS = [
    "#150a98",  # cutoff - deep navy (just darker than linear end)
    "#6f19b4",  # 0.25  - purple
    "#c22dc1",  # 0.50  - magenta
    "#d33189",  # 0.75  - hot pink
    "#dd3949",  # vmax  - coral red
]

# Plotly-compatible colourscale (values 0-1, linear half then log half)
WIKISPIRAL_PLOTLY: list[list] = []
for _i, _hex in enumerate(_LINEAR_STOPS):
    _r = int(_hex[1:3], 16)
    _g = int(_hex[3:5], 16)
    _b = int(_hex[5:7], 16)
    # Last linear stop capped at 0.4999 to avoid a duplicate 0.5 with the
    # first log stop; Plotly treats a duplicate position as the scale end
    # and clamps everything above it to that colour.
    pos = min(_i / (len(_LINEAR_STOPS) - 1) * 0.5, 0.4999)
    WIKISPIRAL_PLOTLY.append([pos, f"rgb({_r},{_g},{_b})"])
for _i, _hex in enumerate(_LOG_STOPS):
    _r = int(_hex[1:3], 16)
    _g = int(_hex[3:5], 16)
    _b = int(_hex[5:7], 16)
    WIKISPIRAL_PLOTLY.append([0.5 + _i / (len(_LOG_STOPS) - 1) * 0.5, f"rgb({_r},{_g},{_b})"])


def auto_cutoff(
    values: npt.ArrayLike,
    vmin: float,
    vmax: float,
) -> float:
    """Compute the linear-to-log threshold using the Tukey IQR fence.

    cutoff = Q3 + 1.5 * IQR  (standard boxplot upper whisker)

    Robust to extreme outliers: the IQR is unaffected by values above Q3,
    so a handful of viral-spike days will not drag the cutoff upward.
    Clamped to [vmin + 5%, vmax - 5%] so both colour segments always exist.
    """
    vals = np.asarray(values, dtype=float)
    vals = vals[np.isfinite(vals)]
    if len(vals) == 0:
        return (vmin + vmax) / 2.0
    q1, q3 = float(np.percentile(vals, 25)), float(np.percentile(vals, 75))
    threshold = q3 + 1.5 * (q3 - q1)
    eps = (vmax - vmin) * 0.05
    return float(np.clip(threshold, vmin + eps, vmax - eps))


class HybridNorm:
    """Map data values to [0, 1] using a linear-then-log hybrid.

    [vmin, cutoff] -> [0.0, 0.5]  linearly
    [cutoff, vmax] -> [0.5, 1.0]  logarithmically
    """

    def __init__(self, vmin: float, vmax: float, cutoff: float) -> None:
        self.vmin = vmin
        self.vmax = vmax
        self.cutoff = cutoff
        self._log_cutoff = np.log10(max(cutoff, 1e-10))
        self._log_vmax = np.log10(max(vmax, 1e-10))

    def __call__(self, values: npt.ArrayLike) -> np.ndarray:
        vals = np.asarray(values, dtype=float)
        result = np.zeros_like(vals)

        lin_mask = vals <= self.cutoff
        log_mask = ~lin_mask

        # Linear: [vmin, cutoff] -> [0, 0.5]
        lin_range = self.cutoff - self.vmin
        if lin_range > 0:
            result[lin_mask] = 0.5 * (vals[lin_mask] - self.vmin) / lin_range
        else:
            result[lin_mask] = 0.0

        # Log: [cutoff, vmax] -> [0.5, 1.0]
        log_range = self._log_vmax - self._log_cutoff
        if log_range > 0:
            log_vals = np.log10(np.maximum(vals[log_mask], 1e-10))
            result[log_mask] = 0.5 + 0.5 * (log_vals - self._log_cutoff) / log_range
        else:
            result[log_mask] = 1.0

        return np.clip(result, 0.0, 1.0)


def make_wikispiral_mpl_cmap(n: int = 256):
    """Build a matplotlib ListedColormap for the WikiSpiral hybrid colour scheme."""
    try:
        import matplotlib.colors as mcolors
    except ImportError:
        raise ImportError("matplotlib is required to build the matplotlib colourmap")

    half = n // 2
    lin_cmap = mcolors.LinearSegmentedColormap.from_list("_lin", _LINEAR_STOPS)
    log_cmap = mcolors.LinearSegmentedColormap.from_list("_log", _LOG_STOPS)
    colours = np.vstack([
        lin_cmap(np.linspace(0, 1, half)),
        log_cmap(np.linspace(0, 1, n - half)),
    ])
    return mcolors.ListedColormap(colours, name="wikispiral")
