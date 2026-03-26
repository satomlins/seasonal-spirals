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
>>> fig, ax = plot_spiral(data, title="Six years of daily data", cmap="plasma")
>>> fig.savefig("spiral.png", dpi=150, bbox_inches="tight")

For more control, use the :class:`SeasonalSpiral` class directly:

>>> spiral = SeasonalSpiral(data, cmap="YlOrRd", ring_width=0.35, log_scale=True)
>>> fig, ax = spiral.plot(show_month_labels=True, colourbar_label="Value")
"""

from seasonal_spirals.spiral import SeasonalSpiral, plot_spiral
from seasonal_spirals.wikipedia import fetch_pageviews, fetch_multiple
from seasonal_spirals.interactive import plot_spiral_interactive

__all__ = [
    "SeasonalSpiral",
    "plot_spiral",
    "plot_spiral_interactive",
    "fetch_pageviews",
    "fetch_multiple",
]
__version__ = "0.1.0"
