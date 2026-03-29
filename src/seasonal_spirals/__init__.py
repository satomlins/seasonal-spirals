"""
seasonal-spirals
================

Visualise time series data as seasonal spiral charts.

A seasonal spiral arranges daily data in a clockwise spiral where each
ring represents one year. Colour encodes the data values, making
year-on-year seasonal patterns immediately visible.

Basic usage
-----------
>>> import pandas as pd
>>> import numpy as np
>>> from seasonal_spirals import plot_spiral
>>>
>>> dates = pd.date_range("2018-01-01", "2023-12-31", freq="D")
>>> data = pd.Series(np.random.default_rng(0).uniform(0, 100, len(dates)), index=dates)
>>> fig = plot_spiral(data, title="Six years of daily data")
>>> fig.show()                          # interactive in notebook
>>> fig.write_image("spiral.png")       # static export (requires kaleido)
>>> fig.write_html("spiral.html")       # standalone HTML

Static matplotlib output (requires ``uv add seasonal-spirals[matplotlib]``)
-----------
>>> from seasonal_spirals import plot_spiral_static
>>> fig, ax = plot_spiral_static(data, title="Six years of daily data", cmap="plasma")
>>> fig.savefig("spiral.png", dpi=150, bbox_inches="tight")
"""

from seasonal_spirals.wikipedia import fetch_pageviews, fetch_multiple
from seasonal_spirals.interactive import plot_spiral

try:
    from seasonal_spirals.spiral import SeasonalSpiral, plot_spiral_static
except ImportError:
    def plot_spiral_static(*args, **kwargs):
        raise ImportError(
            "plot_spiral_static requires matplotlib. "
            "Install it with: uv add seasonal-spirals[matplotlib]"
        )

    def SeasonalSpiral(*args, **kwargs):
        raise ImportError(
            "SeasonalSpiral requires matplotlib. "
            "Install it with: uv add seasonal-spirals[matplotlib]"
        )

__all__ = [
    "SeasonalSpiral",
    "plot_spiral",
    "plot_spiral_static",
    "fetch_pageviews",
    "fetch_multiple",
]
__version__ = "0.2.0"
